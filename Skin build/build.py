"""Build CN dots using the user's own skin. Python 3.9+, standard library only."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, shutil, struct, sys, zipfile, zlib

# CN_PROGRESS_BEGIN
import time
_progress_started = time.monotonic()
_progress_hashes = 0

def progress(message):
    # Reporting must not decide whether compilation succeeds or fails.
    try:
        elapsed = int(time.monotonic() - _progress_started)
        print(f"[{elapsed // 60:02d}:{elapsed % 60:02d}] [BUILD] {message}", flush=True)
    except OSError:
        pass
# CN_PROGRESS_END
def native_path(path):
    p = Path(path).resolve()
    s = str(p)
    if os.name == 'nt' and not s.startswith('\\\\?\\'):
        s = ('\\\\?\\UNC\\' + s[2:]) if s.startswith('\\\\') else ('\\\\?\\' + s)
        return Path(s)
    return p

HERE = native_path(Path(__file__).parent)
DATA = HERE / 'data'
PACKAGE_VARIANT = 'global'
def valid_slot(name):
    return re.fullmatch(r'skin(?:0|[1-9][0-9]*)', name) is not None

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(p):
    # CN_PROGRESS_BEGIN
    global _progress_hashes
    _progress_hashes += 1
    if _progress_hashes % 50 == 0:
        progress(f"Hashing file #{_progress_hashes}: {Path(p).name}")
    # CN_PROGRESS_END
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def toc(raw):
    require(len(raw) >= 56, 'Truncated MCF')
    count = struct.unpack_from('<I', raw, 48)[0]
    end = 52 + count * 16
    require(end + 4 <= len(raw), 'Truncated MCF table')
    require(zlib.crc32(raw[48:end]) == struct.unpack_from('<I', raw, end)[0], 'Invalid MCF table CRC')
    entries = {}
    for i in range(count):
        tag, key, offset, length = struct.unpack_from('<4sIII', raw, 52 + 16*i)
        require(tag == b'IMG ' and key not in entries and offset >= end+4 and offset+length <= len(raw), 'Invalid MCF entry')
        entries[key] = raw[offset:offset+length]
    return entries

def merge_mcf(source, original, dots, profile):
    rules=profile['definition']['build']
    transparent=rules['transparent']
    copies={int(k):v for k,v in rules['copies'][PACKAGE_VARIANT].items()}
    changed_ids={i+1 for i in transparent}|{i+1 for i in copies}
    notice_id=rules.get('sd_notice_export_index')
    if notice_id is not None: notice_id += 1
    # CN_PROGRESS_BEGIN
    progress('Reading and checking image containers')
    # CN_PROGRESS_END
    own, old, patched = toc(source), toc(original), toc(dots)
    require(list(own) == list(old), 'The MCF must have the IDs and order of the selected project base skin; already converted skins are not accepted')
    extra = {k:v for k,v in patched.items() if k not in old}
    require(extra and all(patched[k] == v for k,v in old.items()), 'Inconsistent conversion references')
    require(own[1] == old[1], 'The transparent pixel ID 1 was modified')
    if notice_id is not None:
        require(own[notice_id] == old[notice_id], 'The SD notice background must remain original')
    # CN_PROGRESS_BEGIN
    progress('Adding original CN particles; preserving input images' if profile['definition']['compiler']=='cn_native_v1' else 'Applying the existing B1 image changes and animation maps')
    # CN_PROGRESS_END
    result = dict(own); result.update(extra)
    # Validated Sport/Offroad combination. All unrelated custom images survive.
    for export_id in transparent:
        key = export_id + 1
        blob = result[key]
        w,h = struct.unpack_from('<HH',blob,28)
        require((w,h)==(800,480) and blob[32:36]==bytes.fromhex('04110100'), 'Incompatible Sport/Offroad format')
        compressed = zlib.compress(bytes(w*h*4),9)
        hdr = bytearray(blob[:28]); struct.pack_into('<I',hdr,12,len(compressed))
        struct.pack_into('<I',hdr,24,zlib.crc32(hdr[:24]))
        body = blob[28:36] + compressed
        result[key] = bytes(hdr) + body + struct.pack('<I',zlib.crc32(body))
    for destination,source_index in copies.items():
        blob = bytearray(own[source_index+1])
        struct.pack_into('<I',blob,4,destination+1)
        struct.pack_into('<I',blob,24,zlib.crc32(blob[:24]))
        result[destination+1] = bytes(blob)
    # CN_PROGRESS_BEGIN
    progress('Packing images.mcf')
    # CN_PROGRESS_END
    header = bytearray(source[:48]); count = len(result)
    struct.pack_into('<II', header, 32, 16*count, 16*count)
    struct.pack_into('<I', header, 44, zlib.crc32(header[20:44]))
    table = bytearray(struct.pack('<I', count)); blobs = []; offset = 56 + 16*count
    for key, blob in result.items():
        table.extend(struct.pack('<4sIII', b'IMG ', key, offset, len(blob)))
        blobs.append(blob); offset += len(blob)
    output = bytes(header) + table + struct.pack('<I', zlib.crc32(table)) + b''.join(blobs)
    # CN_PROGRESS_BEGIN
    progress('Verifying the packed images and preserved resources')
    # CN_PROGRESS_END
    reread = toc(output)
    require(all(reread[k] == v for k,v in own.items() if k not in changed_ids), 'Verification failed: an unrelated user image was changed')
    return output, len(own)-len(changed_ids), len(extra), sum(own[k] != old[k] for k in old if k not in changed_ids)

def validate_assets():
    progress('Checking common support files...')
    checked_manifest(DATA)

def readres(raw):
    fmts={2:'b',3:'H',4:'h',5:'i',6:'q',7:'f',8:'d'}
    pos=4; out=[]
    for _ in range(struct.unpack_from('<I',raw)[0]):
        typ,n=struct.unpack_from('<II',raw,pos); pos+=8
        fmt='<'+str(n)+fmts[typ]; values=list(struct.unpack_from(fmt,raw,pos)); pos+=struct.calcsize(fmt)
        out.append((typ,values))
    require(pos==len(raw),'Unexpected trailing RES data')
    return out

def prepare(source, destination, origin, profile):
    assets=profile['root']
    recipe=profile.get('target_recipe', {})
    dots=assets/recipe.get('assets', 'dots')
    extra_files=recipe.get('extra_files', [])
    rules=profile['definition']['build']
    copies={int(k):v for k,v in rules['copies'][PACKAGE_VARIANT].items()}
    changed_ids={i+1 for i in rules['transparent']}|{i+1 for i in copies}
    # CN_PROGRESS_BEGIN
    progress(f"{source.name}: checking input compatibility")
    # CN_PROGRESS_END
    require(source.is_dir(), 'Input folder not found')
    require(valid_slot(source.name), 'Use skinN with a non-negative integer, no spaces or leading zeros: skin3, skin5...')
    _, display_name = labelled_info((source/'info.txt').read_bytes())
    require(not any(p.is_symlink() for p in source.rglob('*')), 'Symbolic links are not allowed')
    check_resource_layout(source, profile)
    verify_profile(profile)
    verify_origin(source, origin)
    raw, existing, appended, custom = merge_mcf((source/'images.mcf').read_bytes(),
            (assets/'original/images.mcf').read_bytes(), (dots/'images.mcf').read_bytes(), profile)
    # CN_PROGRESS_BEGIN
    progress(f"{source.name}: copying input skin; please wait")
    # CN_PROGRESS_END
    verify_origin(source, origin)
    shutil.copytree(source, destination)
    verify_origin(destination, origin)
    # CN_PROGRESS_BEGIN
    progress('Writing compiled image resources')
    # CN_PROGRESS_END
    (destination/'images.mcf').write_bytes(raw)
    # The RES layout was checked byte-for-byte. This adds the known indexed dots
    # and redirects only the documented backgrounds, retaining scaling modes.
    shutil.copyfile(dots/'images.res', destination/'images.res')
    shutil.copyfile(dots/'viewhandler.zip', destination/'viewhandler.zip')
    shutil.copyfile(dots/'skinanim.res', destination/'view/skinanim.res')
    for name in extra_files:
        shutil.copyfile(dots/name, destination/name)
    # Change only the GEM label, keeping every other info.txt property.
    info_path = destination/'info.txt'
    info = info_path.read_bytes()
    labelled, current_name = labelled_info(info)
    require(current_name == display_name, 'Input display name changed during compilation')
    info_path.write_bytes(labelled)
    refs=readres((destination/'images.res').read_bytes()); a=refs[2][1]; half=len(a)//2
    require(len(a)%6==0 and all(a[i+2]==a[half+i+2] for i in range(0,half,3)), 'Incompatible scaling modes')
    # CN_PROGRESS_BEGIN
    progress('Checking all skin files against the input')
    # CN_PROGRESS_END
    modified=[]
    for f in source.rglob('*'):
        if f.is_file() and sha(f)!=sha(destination/f.relative_to(source)):
            modified.append(f.relative_to(source).as_posix())
    expected={'images.mcf','images.res','viewhandler.zip','view/skinanim.res'}
    require(expected <= set(modified) and set(modified) <= expected | {'info.txt'} | set(extra_files), 'Unexpected changes')
    require(all((destination/name).read_bytes()==(dots/name).read_bytes() for name in extra_files), 'Target recipe resource differs')
    return {'source':str(source),'slot':source.name,'user_mcf_entries_preserved':existing,
            'custom_mcf_entries_preserved':custom,'dots_mcf_entries_appended':appended,
            'transparent_background_export_indexes':rules['background_indexes'],
            'original_background_export_indexes':rules['protected_backgrounds'],'display_name':display_name,'combination':recipe.get('combination',rules.get('combination','B1_GLOBAL_INCREMENTAL_P15')),
            'particle_tint_multiplier':rules.get('particle_multiplier',1.15), 'particle_opacity_contrast_multiplier':rules.get('particle_multiplier',1.15),
            'transparent_mcf_export_indexes':rules['transparent'],
            'copied_mcf_export_indexes':copies,
            'intentional_image_replacements':sorted(k-1 for k in changed_ids),
            'modified_skin_files':modified,'all_other_skin_files_identical':True}

# Appended to the proven asset compiler by package_multiskin.py.

def canonical_input(name):
    require(re.fullmatch(r'skin(?:0|[1-9][0-9]*)', name, re.IGNORECASE | re.ASCII),
            'Invalid folder name: use skin2, skin3, skin5, without leading zeros')
    return name.lower()

def same_tree(a, b):
    def inventory(p):
        require(p.is_dir() and not p.is_symlink(), 'Missing or linked folder: '+str(p))
        require(not any(x.is_symlink() for x in p.rglob('*')), 'Links are not allowed')
        # CN_PROGRESS_BEGIN
        progress("Hashing stored result: " + p.name)
        # CN_PROGRESS_END
        return {x.relative_to(p).as_posix():sha(x) for x in p.rglob('*') if x.is_file()}
    return inventory(a) == inventory(b)

def publish_items(items, backup):
    done=[]
    try:
        for index,(source,target) in enumerate(items):
            # CN_PROGRESS_BEGIN
            progress(f"Publishing item {index + 1}/{len(items)}: {target.name}")
            # CN_PROGRESS_END
            require(not target.is_symlink(), 'Linked destination: '+str(target))
            saved=backup/str(index);had=target.exists()
            target.parent.mkdir(parents=True,exist_ok=True)
            if had:
                saved.parent.mkdir(parents=True,exist_ok=True)
                os.replace(target,saved)
            done.append((target,saved,had))
            os.replace(source,target)
    except Exception:
        # CN_PROGRESS_BEGIN
        progress("Publication failed; recovering the previous output")
        # CN_PROGRESS_END
        for target,saved,had in reversed(done):
            if target.is_dir():shutil.rmtree(target)
            elif target.exists():target.unlink()
            if had:os.replace(saved,target)
        raise

"""Injected into the standalone builder; uses only the Python standard library."""

"""Embedded in build.py: registered, explicit project profiles (no MCF whitelist)."""
ORIGIN_NOT_FOUND = ('Skin not found in dump or Skin exception. Check that the copied '
                    'folders contain the same original information.')
COMPATIBILITY_FILES = ('images.res', 'viewhandler.zip', 'view/skinanim.res')
PROJECTS = HERE / 'Projects'


def plain_path(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink(): return False
        try: attributes = getattr(part.lstat(), 'st_file_attributes', 0)
        except FileNotFoundError: continue
        if attributes & 0x400: return False
    return True


def reference_children(folder):
    if not folder.is_dir() or not plain_path(folder): return []
    return sorted((p for p in folder.iterdir() if p.is_dir() and plain_path(p)),
                  key=lambda p: p.name.casefold())


def checked_manifest(root):
    require(plain_path(root), 'Linked profile/support folder: ' + str(root))
    manifest_path = root / 'sha256.json'
    require(manifest_path.is_file() and plain_path(manifest_path), 'Missing or linked manifest: '+str(root))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(isinstance(manifest, dict) and manifest, 'Empty or invalid manifest: '+str(root))
    for rel, expected in manifest.items():
        require(isinstance(rel,str) and re.fullmatch(r'[A-Za-z0-9_. /-]+',rel)
                and not rel.startswith('/') and all(x not in ('','..','.') for x in rel.split('/')),
                'Unsafe manifest path')
        require(isinstance(expected,str) and re.fullmatch('[0-9a-f]{64}',expected), 'Invalid asset hash')
        path = root / rel
        require(path.is_file() and plain_path(path) and sha(path)==expected, 'Damaged or linked asset: '+str(path))
    return manifest


def info_properties(raw):
    result={}
    for line in raw.decode('utf-8-sig').splitlines():
        if not line or line.startswith(('#','!')): continue
        require('=' in line, 'Invalid info.txt property')
        key,value=line.split('=',1)
        require(key not in result, 'Duplicate info.txt property: '+key)
        result[key]=value
    require(result, 'Empty info.txt properties')
    return result


def profile_info(raw):
    # Display names are cosmetic and may have been customized before CN dots.
    values=info_properties(raw); values.pop('skin.displayname',None)
    return values


def load_projects():
    profiles=[]
    for firmware in reference_children(PROJECTS):
        for variant in reference_children(firmware):
            for skin in reference_children(variant):
                definition=skin/'profile.json'
                if not definition.exists(): continue  # Empty placeholders are not supported profiles.
                require(re.fullmatch(r'MST2_[A-Za-z0-9_]+', firmware.name), 'Invalid project firmware folder')
                require(variant.name in ('cpu','cpuplus') and valid_slot(skin.name), 'Invalid project variant/skin folder')
                manifest=checked_manifest(skin)
                require('profile.json' in manifest,'Unverified profile definition')
                profile=json.loads(definition.read_text(encoding='utf-8'))
                require(profile.get('schema')==1 and profile.get('enabled') is True,'Profile is not enabled: '+str(skin))
                require((profile.get('firmware'),profile.get('variant'),profile.get('source_skin'))==
                        (firmware.name,variant.name,skin.name),'Profile identity differs from its folder')
                require(profile.get('compiler') in ('mcf_b1_v1','cn_native_v1'),'Unsupported compiler; profile needs development')
                required=['original/info.txt','original/images.mcf','dots/images.mcf','dots/images.res',
                          'dots/viewhandler.zip','dots/skinanim.res','installer/runtime.ifs',
                          'installer/configuration.res','installer/allowed/stock.res']
                required+=['original/'+name for name in COMPATIBILITY_FILES]
                require(all(name in manifest for name in required),'Incomplete project assets: '+str(skin))
                protected=profile.get('protected_target_slots',[])
                require(isinstance(protected,list) and all(isinstance(n,str) and valid_slot(n) for n in protected),
                        'Invalid protected target slots')
                build=profile.get('build',{})
                require(set(build.get('copies',{}))=={'global','personal'}, 'Missing package-specific image rules')
                for k in ['transparent','background_indexes','protected_backgrounds']:
                    require(isinstance(build.get(k),list) and all(type(n) is int and n>=0 for n in build[k]),'Invalid image rule: '+k)
                if profile['compiler']=='cn_native_v1':
                    require(build.get('sd_notice_export_index') is None and not build['transparent']
                            and not any(build['copies'].values()) and build.get('particle_multiplier')==1.0,
                            'Original CN profile must preserve all input image payloads and native particle values')
                else:
                    require(type(build.get('sd_notice_export_index')) is int and build['sd_notice_export_index']>=0,
                            'Missing original SD notice protection')
                require(isinstance(build.get('display_prefixes'),dict) and
                        all(build['display_prefixes'].get(k) == DISPLAY_PREFIX for k in ['global','personal']),
                        'Invalid display prefix')
                for copies in build['copies'].values():
                    require(isinstance(copies,dict) and all(re.fullmatch(r'0|[1-9][0-9]*',k) and type(v) is int and v>=0
                            for k,v in copies.items()),'Invalid image copy rule')
                notice=build.get('sd_notice_export_index')
                require(notice not in build['transparent'] and all(str(notice) not in c for c in build['copies'].values()),
                        'The SD notification background must stay original')
                recipes=profile.get('target_recipes',{})
                require(isinstance(recipes,dict), 'Invalid target recipes')
                for slot,recipe in recipes.items():
                    require(valid_slot(slot) and isinstance(recipe,dict), 'Invalid target recipe')
                    require(recipe.get('assets')=='dots/'+slot and recipe.get('extra_files')==['ambienceColorMap.res']
                            and isinstance(recipe.get('combination'),str), 'Invalid target recipe assets')
                    require(profile['compiler']=='cn_native_v1', 'Target recipes require native CN compiler')
                    for name in ['images.mcf','images.res','viewhandler.zip','skinanim.res','ambienceColorMap.res']:
                        require(recipe['assets']+'/'+name in manifest, 'Missing verified target recipe resource')
                profiles.append({'root':skin,'definition':profile,'manifest':manifest,
                                 'id':firmware.name+'/'+variant.name+'/'+skin.name})
    require(profiles, 'No enabled project profile found in Skin build/Projects')
    return profiles


def original_info_candidates(sd, home):
    catalogs={'dump':[], 'Skin exception':[]}
    def add(kind, skin, firmware=None, variant=None):
        if re.fullmatch(r'skin(?:0|[1-9][0-9]*)',skin.name,re.I|re.ASCII):
            catalogs[kind].append({'slot':skin.name.lower(),'path':skin/'info.txt',
                                   'firmware':firmware,'variant':variant})
    for firmware in reference_children(sd/'dump'):
        for unit in reference_children(firmware):
            for skin in reference_children(unit/'skins'): add('dump',skin,firmware.name)
            for variant in ['cpu','cpuplus']:
                for skin in reference_children(unit/variant/'skins'): add('dump',skin,firmware.name,variant)
    exceptions=home/'Skin exception'
    for skin in reference_children(exceptions): add('Skin exception',skin)
    for firmware in reference_children(exceptions):
        if not firmware.name.startswith('MST2_'): continue
        # Both explicit variant folders and firmware/skinN evidence are accepted.
        # Missing variant is resolved from verified control resources, never guessed.
        for skin in reference_children(firmware): add('Skin exception',skin,firmware.name)
        for skin in reference_children(firmware/'skins'): add('Skin exception',skin,firmware.name)
        for variant in ['cpu','cpuplus']:
            for skin in reference_children(firmware/variant): add('Skin exception',skin,firmware.name,variant)
            for skin in reference_children(firmware/variant/'skins'): add('Skin exception',skin,firmware.name,variant)
    return list(catalogs.items())


# Embedded in the distributed builder after info_properties().
DISPLAY_PREFIX = '[CN_Dots]-'


def displayname_span(raw):
    # Parse properties first to reject duplicate keys and malformed text. Match
    # only the value bytes; retain the key, BOM, every other byte and line ending.
    values = info_properties(raw)
    name = values.get('skin.displayname')
    require(isinstance(name, str) and name.strip(),
            'info.txt: missing or empty skin.displayname')
    require(not any(ord(c) < 32 or ord(c) == 127 for c in name),
            'info.txt: control characters in skin.displayname')
    matches = list(re.finditer(rb'(?:\A(?:\xef\xbb\xbf)?|(?<=[\r\n]))skin\.displayname=([^\r\n]*)', raw))
    require(len(matches) == 1 and matches[0].group(1).decode('utf-8') == name,
            'info.txt: ambiguous skin.displayname')
    return matches[0].span(1), name


def origin_info(raw):
    (start, end), _ = displayname_span(raw)
    return raw[:start] + raw[end:]


def labelled_info(raw):
    (start, end), name = displayname_span(raw)
    while name.startswith(DISPLAY_PREFIX):
        name = name[len(DISPLAY_PREFIX):]
    require(name.strip(), 'info.txt: skin.displayname must contain a name after the CN Dots prefix')
    label = DISPLAY_PREFIX + name
    return raw[:start] + label.encode('utf-8') + raw[end:], label


def check_origin(source, target_slot, catalogs):
    path = source/'info.txt'
    require(path.is_file() and plain_path(path), ORIGIN_NOT_FOUND+' Input info.txt is missing or linked.')
    info = path.read_bytes()
    comparable = origin_info(info)
    for kind, candidates in catalogs:
        matches = []
        snapshots = {}
        for ref in candidates:
            candidate = ref['path']
            if not candidate.is_file() or not plain_path(candidate):
                continue
            raw = candidate.read_bytes()
            try:
                same = origin_info(raw) == comparable
            except (ValueError, UnicodeError):
                continue  # Malformed catalog entries cannot establish origin.
            if same:
                matches.append(ref)
                snapshots[str(candidate)] = hashlib.sha256(raw).hexdigest()
        if not matches:
            continue
        slots = {ref['slot'] for ref in matches}
        firmwares = {ref['firmware'] for ref in matches if ref['firmware']}
        variants = {ref['variant'] for ref in matches if ref['variant']}
        require(len(slots) == 1 and len(firmwares) <= 1 and len(variants) <= 1,
                'Ambiguous origin references: multiple source slots, firmwares or variants. Keep only the correct origin evidence.')
        return {'reference_type': kind, 'original_slot': next(iter(slots)), 'target_slot': target_slot,
                'firmware_hint': next(iter(firmwares), None), 'variant_hint': next(iter(variants), None),
                'input_info_sha256': hashlib.sha256(info).hexdigest(),
                'comparison': 'Exact bytes except the skin.displayname value; all other bytes and line endings preserved',
                'matching_references': [str(ref['path']) for ref in matches],
                'reference_info_sha256': snapshots}
    raise ValueError(ORIGIN_NOT_FOUND+' Input: '+source.name)


def verify_origin(source, origin):
    require(origin['target_slot'] == canonical_input(source.name), 'The input folder name changed after origin verification.')
    path = source/'info.txt'
    require(path.is_file() and plain_path(path), 'Input info.txt is missing or linked after origin verification.')
    info = path.read_bytes()
    # The exemption applies only to matching origin evidence. Once verified,
    # even a label-only edit during this build must invalidate the snapshot.
    require(hashlib.sha256(info).hexdigest() == origin['input_info_sha256'], 'Input info.txt changed after origin verification.')
    comparable = origin_info(info)
    for name in origin['matching_references']:
        ref = Path(name)
        require(ref.is_file() and plain_path(ref), 'Reference info.txt missing or linked after origin verification.')
        raw = ref.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == origin['reference_info_sha256'][name]
                and origin_info(raw) == comparable, 'Reference info.txt changed after origin verification.')


def identify_project(source, origin, profiles):
    properties=profile_info((source/'info.txt').read_bytes())
    controls={}
    for rel in COMPATIBILITY_FILES:
        path=source/rel
        require(path.is_file() and plain_path(path),'Missing or linked compatibility resource: '+rel)
        controls[rel]=sha(path)
    matches=[]
    for profile in profiles:
        p=profile['definition'];root=profile['root']
        if origin['firmware_hint'] and p['firmware']!=origin['firmware_hint']:continue
        if origin['variant_hint'] and p['variant']!=origin['variant_hint']:continue
        if profile_info((root/'original/info.txt').read_bytes())!=properties:continue
        if any(controls[rel]!=profile['manifest']['original/'+rel] for rel in COMPATIBILITY_FILES):continue
        matches.append(profile)
    require(matches,'No supported project profile matches this skin: '+source.name+
            '. Check firmware/variant references and original control resources. Empty Projects folders are not supported yet.')
    require(len(matches)==1,'Ambiguous project profile: '+', '.join(p['id'] for p in matches)+
            '. Multiple supported projects match; keep the correct original reference and review the project definitions.')
    profile=matches[0];p=profile['definition']
    require(origin['target_slot'] not in p.get('protected_target_slots',[]),
            'Protected target '+origin['target_slot']+' must remain unchanged for '+p['firmware'])
    origin['resolved_firmware']=p['firmware']
    origin['resolved_variant']=p['variant']
    origin['resolved_source_skin']=p['source_skin']
    progress(p['source_skin']+' match with '+p['firmware']+' >'+p['variant']+'<')
    progress('Origin reference: '+origin['original_slot']+'; destination: '+origin['target_slot']+'. Continuing...')
    selected=dict(profile)
    selected['target_recipe']=p.get('target_recipes',{}).get(origin['target_slot'],{})
    if selected['target_recipe']:
        progress('Target recipe: '+origin['target_slot']+' / '+selected['target_recipe']['combination'])
    return selected


def project_identity(profile):
    identity={k:profile['definition'][k] for k in ['firmware','variant','source_skin','compiler']}
    if profile.get('target_recipe'):identity['target_recipe']=profile['target_recipe']['combination']
    return identity


def check_resource_layout(source, profile):
    checked={}
    for rel in COMPATIBILITY_FILES:
        path=source/rel
        require(path.is_file() and plain_path(path),'Missing or linked compatibility resource: '+rel)
        require(path.read_bytes()==(profile['root']/'original'/rel).read_bytes(),rel+': incompatible base for '+profile['id'])
        checked[rel]=sha(path)
    return {'profile':project_identity(profile),'checked_resources_sha256':checked,'images_mcf_used_for_origin_filter':False}


def verify_profile(profile):
    require(checked_manifest(profile['root'])==profile['manifest'],'Project assets changed during compilation')


def installer_identity(profile):
    return {name[len('installer/'):]:digest for name,digest in profile['manifest'].items()
            if name.startswith('installer/')}


def check_project_batch(profiles):
    group=next(iter(profiles.values()))
    target=(group['definition']['firmware'],group['definition']['variant'])
    for p in profiles.values():
        require((p['definition']['firmware'],p['definition']['variant'])==target,
                'Different firmware/variant profiles cannot share one installation SD. Use a separate SD/output for each target.')
        require(installer_identity(p)==installer_identity(group),'Selected profiles require different shared installer resources')
    return group


def write_project_metadata(folder, profile):
    p=profile['definition']
    for name,value in [('profile_firmware.txt',p['firmware']),('profile_variant.txt',p['variant']),('profile_source_skin.txt',p['source_skin'])]:
        (folder/name).write_bytes((value+'\n').encode('ascii'))
    (folder/'profile.json').write_text(json.dumps(project_identity(profile),indent=2),encoding='utf-8')


def check_previous_projects(results, support, group):
    for folder in reference_children(results):
        meta=support/'generated'/folder.name/'profile.json'
        require(meta.is_file() and plain_path(meta), 'Previous output has no project identity. Archive it outside output and rebuild from input: '+folder.name)
        old=json.loads(meta.read_text(encoding='utf-8'));new=group['definition']
        require(old.get('firmware')==new['firmware'] and old.get('variant')==new['variant'],
                'Previous output belongs to a different firmware/variant: '+folder.name)


BUILD_STATE_VERSION = 2


def tree_identity(folder):
    """Change detection only; this is NOT an images.mcf compatibility whitelist."""
    require(folder.is_dir() and plain_path(folder), 'Missing or linked folder: ' + str(folder))
    result = {}
    for path in sorted(folder.rglob('*')):
        require(plain_path(path), 'Linked paths are not allowed: ' + str(path))
        name = path.relative_to(folder).as_posix()
        if path.is_dir():
            result[name + '/'] = {'directory': True}
        else:
            require(path.is_file(), 'Unsupported input entry: ' + name)
            result[name] = {'size': path.stat().st_size, 'sha256': sha(path)}
    return result


def identity_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def recipe_identity(profile):
    return identity_digest({'builder':sha(HERE/'build.py'), 'project':project_identity(profile),
        'project_assets':profile['manifest'], 'common_assets':json.loads((DATA/'sha256.json').read_text())})


def current_build(source_identity, recipe, output, metadata):
    state_path = metadata / 'build_state.json'
    if not state_path.is_file() or not output.is_dir():
        return False
    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if (state.get('version') != BUILD_STATE_VERSION or state.get('recipe') != recipe
                or state.get('input') != source_identity):
            return False
        actual = tree_identity(output)
        return (state.get('output') == actual
                and tree_identity(metadata / 'reference') == actual
                and (metadata / 'build_id.txt').read_text().strip() == identity_digest(actual))
    except (OSError, ValueError, KeyError):
        return False


def save_build_state(metadata, source_identity, recipe, skin):
    output_identity = tree_identity(skin)
    (metadata / 'build_id.txt').write_bytes((identity_digest(output_identity) + '\n').encode('ascii'))
    (metadata / 'build_state.json').write_text(json.dumps({
        'version': BUILD_STATE_VERSION, 'recipe': recipe,
        'input': source_identity, 'output': output_identity,
        'purpose': 'Incremental change detection; not source compatibility approval'
    }, indent=2), encoding='utf-8')


def main():
    # CN_PROGRESS_BEGIN
    progress('Starting Skin build')
    # CN_PROGRESS_END
    parser=argparse.ArgumentParser(description='Build multiple skins after verifying their original info.txt; preserve output/skinN.')
    parser.add_argument('--source',type=Path,action='append',help='Input skinN folder; --source may be repeated')
    parser.add_argument('--sd-root',type=Path,default=HERE.parent)
    args=parser.parse_args();validate_assets()
    progress('Loading registered project profiles...')
    if (DATA/'compact_distribution.json').is_file():
        import importlib.util
        spec=importlib.util.spec_from_file_location('cn_compact_assets', DATA/'compact_assets.py')
        compact=importlib.util.module_from_spec(spec);spec.loader.exec_module(compact)
        compact.prepare(HERE,progress)
    registered=load_projects()
    sd=native_path(args.sd_root)
    require((sd/'toolbox').is_dir(), 'Toolbox folder not found at the target SD root')
    home=sd/'Skin build';results=home/'output'
    support=sd/'toolbox/custom/skins/cn_variant_dots'
    # CN_PROGRESS_BEGIN
    progress('Finding input skins')
    # CN_PROGRESS_END
    sources=args.source or [p for p in (HERE/'input').iterdir() if p.is_dir()]
    require(sources, 'Place one or more compatible skinN folders inside input')
    slots={}
    for source in sources:
        require(plain_path(source), 'Linked input paths are not allowed')
        source=native_path(source);slot=canonical_input(source.name)
        require(slot not in slots,'Duplicate skin number: '+slot)
        require(source.is_dir() and not source.is_symlink(),'Invalid input')
        require(not any(p.is_symlink() for p in source.rglob('*')), 'Links are not allowed in the input')
        require(not source.is_relative_to(results) if hasattr(source,'is_relative_to') else results not in source.parents,
                'Use the original input, not an already converted output')
        slots[slot]=source
    # CN_PROGRESS_BEGIN
    progress('Verifying original info.txt against dump or Skin exception...')
    catalogs = original_info_candidates(sd, home)
    origins = {slot: check_origin(source, slot, catalogs) for slot, source in slots.items()}
    for slot, source in slots.items():
        verify_origin(source, origins[slot])
    progress('Identifying firmware, variant and source skin...')
    profiles={slot:identify_project(source,origins[slot],registered) for slot,source in slots.items()}
    group=check_project_batch(profiles)
    check_previous_projects(results,support,group)
    compatibility={slot:check_resource_layout(source,profiles[slot]) for slot,source in slots.items()}
    progress('Checking previously generated results')
    # CN_PROGRESS_END
    if results.exists():
        require(not results.is_symlink(),'output must not be a link')
        for p in results.iterdir():
            if p.name=='LEEME.txt' and p.is_file():continue
            require(valid_slot(p.name) and p.is_dir() and not p.is_symlink(),
                    'Move incompatible previous content outside output: '+p.name)
            require(same_tree(p,support/'generated'/p.name/'reference'),
                    'Previous result modified or missing its reference: '+p.name)
    recipes={slot:recipe_identity(profile) for slot,profile in profiles.items()}
    identities = {slot: tree_identity(source) for slot, source in slots.items()}
    skipped = {slot for slot in slots if current_build(identities[slot], recipes[slot],
               results/slot, support/'generated'/slot)}
    for slot in sorted(skipped):
        progress('Skipping ' + slot + ': input and compiled output are unchanged.')
    # Do not republish identical support/menu trees either; this preserves timestamps.
    # Installer files supplied by the selected profile override common helpers.
    # Compare the effective tree so VW overrides do not force repeated rebuilds.
    effective_support = {p.relative_to(DATA/'support'):p for p in (DATA/'support').rglob('*') if p.is_file()}
    effective_support.update({p.relative_to(group['root']/'installer'):p
                             for p in (group['root']/'installer').rglob('*') if p.is_file()})
    support_current = all((support/rel).is_file() and sha(support/rel)==sha(p)
                          for rel,p in effective_support.items())
    for key in ['firmware','variant']:
        p=support/('project_'+key+'.txt')
        support_current = support_current and p.is_file() and p.read_bytes()==(group['definition'][key]+'\n').encode('ascii')
    menu_current = all((sd/'custom/greenmenu'/p.relative_to(DATA/'greenmenu')).is_file()
                       and sha(sd/'custom/greenmenu'/p.relative_to(DATA/'greenmenu')) == sha(p)
                       for p in (DATA/'greenmenu').rglob('*') if p.is_file())
    if len(skipped) == len(slots) and support_current and menu_current:
        print('BUILD OK: all input skins are unchanged; nothing rebuilt.')
        return
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run=home/'historial'/stamp;stage=run/'preparacion';stage.mkdir(parents=True)
    next_support=stage/'support'
    # CN_PROGRESS_BEGIN
    progress('Copying installer support into the build staging folder')
    # CN_PROGRESS_END
    shutil.copytree(DATA/'support',next_support)
    shutil.copytree(group['root']/'installer',next_support,dirs_exist_ok=True)
    for key in ['firmware','variant']:
        (next_support/('project_'+key+'.txt')).write_bytes((group['definition'][key]+'\n').encode('ascii'))
    if (support/'generated').exists():
        require((support/'format.txt').read_bytes()==b'multiskin-v1\n','Generated support belongs to another version')
        require(not any(p.is_symlink() for p in (support/'generated').rglob('*')),'Linked support files are not allowed')
        # CN_PROGRESS_BEGIN
        progress('Preserving references for the other compiled skins')
        # CN_PROGRESS_END
        shutil.copytree(support/'generated',next_support/'generated')
    reports=[];items=[]
    for slot,source in sorted(slots.items(),key=lambda kv:int(kv[0][4:])):
        if slot in skipped:
            continue
        # CN_PROGRESS_BEGIN
        progress(f"Building {slot} ({len(reports) + 1}/{len(slots)})")
        # CN_PROGRESS_END
        normalized=source
        if source.name!=slot:
            normalized=stage/'input_normalizada'/slot
            # CN_PROGRESS_BEGIN
            progress(f"{slot}: copying input to normalize the folder name")
            # CN_PROGRESS_END
            shutil.copytree(source,normalized)
        skin=stage/'output'/slot
        report=prepare(normalized,skin,origins[slot],profiles[slot])
        report['project_profile']=project_identity(profiles[slot])
        report['origin_verification']=origins[slot]
        report['compatibility_verification']=compatibility[slot]
        report['source']=str(source);report['slot']=slot
        report['selection_rule']='Only folders currently present in Skin build/output'
        generated=next_support/'generated'/slot
        if generated.exists():shutil.rmtree(generated)
        # CN_PROGRESS_BEGIN
        progress(f"{slot}: saving the compiled reference copy")
        # CN_PROGRESS_END
        shutil.copytree(skin,generated/'reference')
        require(tree_identity(source) == identities[slot],
                'Input changed during compilation. Nothing published; run build.cmd again.')
        save_build_state(generated, identities[slot], recipes[slot], skin)
        write_project_metadata(generated, profiles[slot])
        (generated/'target_slot.txt').write_bytes((slot+'\n').encode('ascii'))
        (generated/'informe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        items.append((skin,results/slot));reports.append(report)
        # CN_PROGRESS_BEGIN
        progress(f"{slot}: build and verification complete")
        # CN_PROGRESS_END
    items.append((next_support,support))
    progress('Preparing GreenMenu files for manual import')
    for rel in ['cn-variant-dots.esd', 'scripts/cn_variant_dots.sh', 'scripts/cn_variant_dots_restore.sh', 'scripts/cn_variant_dots_clean.sh', 'scripts/cn_variant_dots_status.sh']:
        staged_menu=stage/'greenmenu'/rel
        staged_menu.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(DATA/'greenmenu'/rel,staged_menu)
        items.append((staged_menu,sd/'custom/greenmenu'/rel))
    (run/'informe.json').write_text(json.dumps({'skins':reports,'skipped':sorted(skipped),'preserved_other_results':True,
        'backups_on_unit_and_sd_not_modified':True,'saved_previous_paths':
        {str(i):str(target) for i,(_,target) in enumerate(items)}},ensure_ascii=False,indent=2),encoding='utf-8')
    # CN_PROGRESS_BEGIN
    progress('Publishing results and archiving any previous output')
    # CN_PROGRESS_END
    for slot, source in slots.items():
        verify_origin(source, origins[slot])
        require(tree_identity(source) == identities[slot],
                'Input changed during compilation. Nothing published; run build.cmd again.')
    for profile in profiles.values(): verify_profile(profile)
    publish_items(items,run/'respaldo_previo')
    # CN_PROGRESS_BEGIN
    progress("All selected skins generated successfully")
    # CN_PROGRESS_END
    print('BUILD OK: '+', '.join(sorted(slots)))
    print('Outputs: '+str(results))
    print('Other skins in output are preserved. All folders present there are SELECTED.')
    print('In GEM: Customization > CN Variant dots > Install CN Variant dots skins / Uninstall CN Variant dots skins.')
    print('Removing a folder from output only changes selection; it does not delete unit skins or backups.')
    print('Build history: '+str(run))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr);sys.exit(1)
