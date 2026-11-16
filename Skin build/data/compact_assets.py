"""Lossless distribution bootstrap. Writes only missing project/support resources."""
from pathlib import Path
import hashlib,json,lzma,os,shutil,tempfile

CHUNK=1024*1024

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(CHUNK),b''):h.update(block)
    return h.hexdigest()

def plain(path):
    for p in (path,*path.parents):
        require(not p.is_symlink(),'Linked resource path is not allowed: '+str(p))
        try:attr=getattr(p.lstat(),'st_file_attributes',0)
        except FileNotFoundError:continue
        require(not attr&0x400,'Junction resource path is not allowed: '+str(p))

def relative(root,name,prefixes):
    require(isinstance(name,str) and '\\' not in name and ':' not in name,'Invalid resource path')
    parts=name.split('/')
    require(parts and all(p not in ('','..','.') for p in parts),'Invalid resource path')
    require(parts[0] in prefixes,'Resource path outside the permitted folders')
    path=root.joinpath(*parts);plain(path)
    return path

def copy_missing(source,target,expected,scratch):
    plain(target)
    if target.exists():
        require(target.is_file(),'Resource destination is not a file: '+str(target))
        return False
    require(digest(source)==expected,'Resource checksum mismatch: '+str(source))
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='resource-',suffix='.tmp',dir=str(scratch));os.close(fd)
    temporary=Path(name)
    try:
        shutil.copyfile(source,temporary)
        require(digest(temporary)==expected,'Copied resource checksum mismatch')
        require(not target.exists(),'Resource appeared during preparation; run build.cmd again')
        # os.rename refuses to replace an existing file on the supported Windows host.
        temporary.rename(target)
    finally:
        if temporary.exists():temporary.unlink()
    return True

def expand_project(root,progress,scratch):
    metadata=root/'compact.json';plain(metadata)
    spec=json.loads(metadata.read_text(encoding='utf-8'))
    require(spec.get('schema')==1,'Unknown compact resource format')
    asset_manifest=json.loads((root/'sha256.json').read_text(encoding='utf-8'))
    require(asset_manifest.get('compact.json')==digest(metadata),'Compact metadata checksum mismatch')
    objects=spec.get('objects');require(isinstance(objects,list) and objects,'Empty compact resources')
    destinations=set();missing=False
    for obj in objects:
        require(type(obj.get('size')) is int and 0<=obj['size']<=512*1024*1024,'Invalid resource size')
        require(isinstance(obj.get('sha256'),str) and len(obj['sha256'])==64
                and all(c in '0123456789abcdef' for c in obj['sha256']),'Invalid resource digest')
        require(isinstance(obj.get('paths'),list) and obj['paths'],'Missing resource destinations')
        for name in obj['paths']:
            require(name not in destinations,'Repeated resource destination');destinations.add(name)
            require(asset_manifest.get(name)==obj['sha256'],'Resource is not in the project manifest')
            target=relative(root,name,{'original','dots','installer'})
            require(not target.exists() or target.is_file(),'Resource destination is not a file')
            missing |= not target.exists()
    if not missing:return
    require(sum(o['size'] for o in objects)<=2*1024*1024*1024,'Compact project is too large')
    pack=root/'resources.pack.xz';plain(pack)
    require(pack.is_file() and digest(pack)==spec.get('pack_sha256'),'Compressed resources are missing or damaged')
    progress('Preparing compressed project resources...')
    with lzma.open(pack,'rb') as stream:
        for obj in objects:
            targets=[relative(root,n,{'original','dots','installer'}) for n in obj['paths']]
            pending=[p for p in targets if not p.exists()]
            temporary=None;writer=None
            try:
                if pending:
                    pending[0].parent.mkdir(parents=True,exist_ok=True)
                    fd,name=tempfile.mkstemp(prefix='resource-',suffix='.tmp',dir=str(scratch))
                    temporary=Path(name);writer=os.fdopen(fd,'wb')
                remaining=obj['size'];h=hashlib.sha256()
                while remaining:
                    block=stream.read(min(CHUNK,remaining))
                    require(block,'Compressed resource stream is truncated')
                    remaining-=len(block);h.update(block)
                    if writer:writer.write(block)
                if writer:writer.close();writer=None
                require(h.hexdigest()==obj['sha256'],'Decompressed resource checksum mismatch')
                if temporary:
                    for target in pending:copy_missing(temporary,target,obj['sha256'],scratch)
            finally:
                if writer:writer.close()
                if temporary and temporary.exists():temporary.unlink()
        require(stream.read(1)==b'','Unexpected bytes after compressed resources')
    progress('Project resources verified.')

def expand_shared(home,setup,progress,scratch):
    """Recover byte-identical assets from one pool shared by all source profiles."""
    expected={}
    for name in setup['profiles']:
        root=relative(home,name,{'Projects'})
        metadata=root/'compact.json';plain(metadata)
        spec=json.loads(metadata.read_text(encoding='utf-8'))
        require(spec.get('schema')==2,'Unknown shared project format')
        manifest_path=root/'sha256.json';plain(manifest_path)
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        require(manifest.get('compact.json')==digest(metadata),'Compact metadata checksum mismatch')
        objects=spec.get('objects')
        require(isinstance(objects,list) and objects,'Empty compact resources')
        for obj in objects:
            validate_object(obj)
            for rel in obj['paths']:
                relative(root,rel,{'original','dots','installer'})
                require(manifest.get(rel)==obj['sha256'],'Resource is not in the project manifest')
                dest=name+'/'+rel
                require(dest not in expected,'Repeated resource destination')
                expected[dest]=(obj['sha256'],obj['size'])
    pool=setup.get('shared_pack')
    require(isinstance(pool,dict) and pool.get('path')=='Projects/resources.pack.xz','Invalid shared pack path')
    objects=pool.get('objects')
    require(isinstance(objects,list) and objects,'Empty shared resources')
    seen=set();hashes=set();missing=False;total=0
    for obj in objects:
        validate_object(obj)
        require(obj['sha256'] not in hashes,'Repeated shared resource object')
        hashes.add(obj['sha256']);total+=obj['size']
        for name in obj['paths']:
            require(name not in seen,'Repeated shared resource destination');seen.add(name)
            target=relative(home,name,{'Projects'})
            require(expected.get(name)==(obj['sha256'],obj['size']),'Shared resource does not match the project manifests')
            require(not target.exists() or target.is_file(),'Resource destination is not a file')
            missing |= not target.exists()
    require(seen==set(expected),'Shared pack is missing project resources')
    require(total<=2*1024*1024*1024,'Shared resource pool is too large')
    if not missing:return
    pack=relative(home,pool['path'],{'Projects'})
    require(pack.is_file() and digest(pack)==pool.get('sha256'),'Compressed resources are missing or damaged')
    progress('Preparing shared project resources...')
    with lzma.open(pack,'rb') as stream:
        for obj in objects:
            targets=[relative(home,n,{'Projects'}) for n in obj['paths']]
            pending=[p for p in targets if not p.exists()]
            temporary=None;writer=None
            try:
                if pending:
                    fd,name=tempfile.mkstemp(prefix='resource-',suffix='.tmp',dir=str(scratch))
                    temporary=Path(name);writer=os.fdopen(fd,'wb')
                remaining=obj['size'];h=hashlib.sha256()
                while remaining:
                    block=stream.read(min(CHUNK,remaining))
                    require(block,'Compressed resource stream is truncated')
                    remaining-=len(block);h.update(block)
                    if writer:writer.write(block)
                if writer:writer.close();writer=None
                require(h.hexdigest()==obj['sha256'],'Decompressed resource checksum mismatch')
                if temporary:
                    for target in pending:copy_missing(temporary,target,obj['sha256'],scratch)
            finally:
                if writer:writer.close()
                if temporary and temporary.exists():temporary.unlink()
        require(stream.read(1)==b'','Unexpected bytes after compressed resources')
    progress('Shared project resources verified.')


def validate_object(obj):
    require(isinstance(obj,dict),'Invalid resource object')
    require(type(obj.get('size')) is int and 0<=obj['size']<=512*1024*1024,'Invalid resource size')
    require(isinstance(obj.get('sha256'),str) and len(obj['sha256'])==64
            and all(c in '0123456789abcdef' for c in obj['sha256']),'Invalid resource digest')
    require(isinstance(obj.get('paths'),list) and obj['paths'],'Missing resource destinations')
    require(all(isinstance(p,str) for p in obj['paths']),'Invalid resource path')


def prepare_resources(home,progress,scratch):
    home=Path(home);plain(home)
    config=home/'data/compact_distribution.json';plain(config)
    setup=json.loads(config.read_text(encoding='utf-8'))
    require(setup.get('schema') in (1,2),'Unknown compact distribution format')
    profiles=setup.get('profiles');require(isinstance(profiles,list) and profiles,'No compact projects')
    require(all(isinstance(n,str) for n in profiles) and len(profiles)==len(set(profiles)),'Invalid compact project list')
    for name in profiles:
        profile=relative(home,name,{'Projects'})
        require(len(name.split('/'))==4,'Invalid compact project directory')
    if setup['schema']==2:
        expand_shared(home,setup,progress,scratch)
    else:
        for name in profiles:expand_project(relative(home,name,{'Projects'}),progress,scratch)
    default=setup.get('runtime_profile');require(default in profiles,'Unknown runtime project')
    profile=relative(home,default,{'Projects'})
    identity=json.loads((profile/'profile.json').read_text(encoding='utf-8'))
    support=home.parent/'toolbox/custom/skins/cn_variant_dots';plain(support)
    # A previously prepared different target must never receive this default's resources.
    for key in ('firmware','variant'):
        path=support/('project_'+key+'.txt');plain(path)
        require(path.is_file(),'Missing runtime profile metadata')
        if path.read_text().strip()!=identity[key]:return
    manifest=json.loads((profile/'sha256.json').read_text(encoding='utf-8'))
    changed=False
    for rel,expected in manifest.items():
        if not rel.startswith('installer/'):continue
        source=relative(profile,rel,{'installer'})
        name=rel[len('installer/'):]
        target=relative(support,name,{'runtime.ifs','configuration.res','allowed','status_refs','runtime_guard','engine.sh','maintenance.sh','format.txt'})
        changed |= copy_missing(source,target,expected,scratch)
    if changed:progress('Installer resources prepared and verified.')

def prepare(home,progress=print):
    home=Path(home);plain(home/'data')
    # Interrupted temporary data can never enter project assets or unit payloads.
    with tempfile.TemporaryDirectory(prefix='cn-expand-',dir=str(home/'data')) as scratch:
        prepare_resources(home,progress,Path(scratch))
