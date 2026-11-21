#!/usr/bin/env python3
"""Run the actual generated startup and reject incompatible image inputs."""
from pathlib import Path
import json
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[3]
out = root / 'build/switch-runtime'
binary = out / 'host/ngb-startup'
xbe = root / 'game_files/default.xbe'
results = []

def run(name, path, status, required, forbidden=(), data=None, timing=None):
    if data is None:
        with tempfile.TemporaryDirectory(prefix='ngb-data-') as temporary:
            return run(name, path, status, required, forbidden, temporary, timing)
    command = [str(binary), str(path), str(data)]
    if timing:
        command = [str(out / 'host/ngb-runtime-test'), timing, str(path.parent), str(data)]
    p = subprocess.run(command, capture_output=True, text=True, timeout=30,
                       env={**os.environ, "NGB_TEST_VISIBLE_FRAME":"1", "NGB_FULL_TRACE":"1"})
    log = p.stdout + p.stderr
    (out / f'verify-{name}.log').write_text(log)
    assert p.returncode == status, (name, p.returncode, log[-1000:])
    assert all(s in log for s in required), (name, [s for s in required if s not in log], log[-1000:])
    assert not any(s in log for s in forbidden), (name, log[-1000:])
    results.append({'test': name, 'status': 'passed', 'exit_code': p.returncode})
    return log

expected_stop = 'verified visible guest frame: 0x00000040'
startup_markers = [
    '[LOADER] 16 sections, 145 kernel imports',
    '[TLS] block=00008000 size=180',
    '[THREAD] initial handoff routine=003298ad',
    '[KERNEL] 277 RtlEnterCriticalSection',
    '[KERNEL] 294 RtlLeaveCriticalSection',
    '[ENTER] 0032b311',
    '[BOOT] NGB Switch startup adapter 0.49.0',
    '[SHUTDOWN] register registration=004168e8',
    '[TIMER] armed object=00c0eca0 delay_100ns=216000000000 period_ms=0',
    '[VM] allocate base=01000000 bytes=1048576 flags=2000 status=00000000',
    '[VM] allocate base=01000000 bytes=4096 flags=1000 status=00000000',
    'TitleMeta.xbx',
    'TitleImage.xbx',
    'SaveImage.xbx',
    'requested=512 transferred=512 status=00000000',
    r'link \??\Z: -> \Device\Harddisk0\Partition5 status=00000000',
    r'open link \??\D: status=00000000',
    r'target=\Device\CdRom0 bytes=14',
    '[MEMORY] readback passed va=84000000 bytes=38215680',
    '[MEMORY] readback passed va=86472000 bytes=2097152',
    '[KERNEL] 129 KeRaiseIrqlToDpcLevel',
    '[KERNEL] 161 KfLowerIrql',
    r'[SERVICE] created device name=\Device\MU_0 type=0000003a extension=368',
    '[MEMORY] lock pages va=86672000 bytes=8192',
    '[MEMORY] first guest access va=86672000 bytes=4 function=003da2e3',
    '[KERNEL] 44 HalGetInterruptVector caller=003d9f4a',
    '[IRQ] bus=1 vector=31 irql=26',
    '[SERVICE] OHCI0 read offset=00 value=00000010',
    '[SERVICE] OHCI0 write offset=08 value=00000001',
    '[SERVICE] OHCI0 write offset=18 value=06672000',
    '[SERVICE] OHCI0 write offset=20 value=06672580',
    '[IRQ] initialized object=00c0ece0 vector=31 routine=003dfe3d',
    '[IRQ] connected bus=1 object=00c0ece0',
    'OHCI0 port 1 connected',
    '[IRQ] returned routine=003dfe3d pending=40 handled=1',
    '[DPC] dispatch object=80000bc4 routine=003e0511',
    '[DPC] returned object=80000bc4',
    '[D3D] Direct3D_CreateDevice entry=003cc310',
    'alignment=4096 protect=00000404 va=86675000',
    'NV2A read addr=fd001804 value=00000000',
    'NV2A write addr=fd001804 value=00000004',
    'NV2A write addr=fd600140 value=00000000',
    'NV2A write addr=fd009140 value=00000000',
    'NV2A read addr=fd001800 value=02a010de',
    'NV2A read addr=fd001808 value=030000a1',
    'NV2A read addr=fd10020c value=08000000',
    '[IRQ] bus=3 vector=33 irql=24',
    '[IRQ] initialized object=003d7b5c vector=33 routine=003cf980',
    '[KERNEL] 98 KeConnectInterrupt caller=003cefa1',
    '[IRQ] connected bus=3 object=003d7b5c',
    '[SHUTDOWN] register registration=003d7cac',
    'NV2A write addr=fd001830 value=00000000',
    'NV2A write addr=fd00180c value=0000f800',
    'NV2A read addr=fd000200 value=00000000',
    'NV2A write addr=fd000200 value=ffffffff',
    'NV2A read8 addr=fd680505 value=00000000',
    'NV2A read8 addr=fd680509 value=000000c2',
    'NV2A read8 addr=fd680501 value=0000001c',
    'NV2A write addr=fd009200 value=0000de86',
    'NV2A write addr=fd009210 value=00001dcd',
    'NV2A write addr=fd009420 value=ffffffff',
    'NV2A read addr=fd001218 value=00000000',
    '[KERNEL] 168 MmClaimGpuInstanceMemory caller=003d2df2',
    '[MEMORY] GPU instance claim bytes=20480 padding_out=',
    'top=87ff0000 padding=00010000',
    'NV2A write addr=fd002210 value=03000100',
    'NV2A write addr=fd002214 value=00890110',
    'NV2A PRAMIN write addr=fd710000 value=00000000',
    'NV2A PRAMIN write addr=fd714ffc value=00000000',
    'NV2A write8 addr=fd6013d5 value=00000099',
    'NV2A write addr=fd600804 value=00000002',
    'NV2A write addr=fd008944 value=00100000',
    'NV2A write addr=fd400780 value=0000110a',
    'NV2A write addr=fd003240 value=00000000',
    '[PORT] encoder GPIO=01',
    'NV2A read addr=fd00184c value=1f000000',
    'NV2A write addr=fd009410 value=00000000',
    'NV2A write addr=fd002140 value=01111111',
    'NV2A USER write addr=fd800040 value=06675000',
    'NV2A DMA jump addr=00000000 value=06675000',
    'NV2A USER read addr=fd800044 value=06675000',
    'NV2A read addr=fd400900 value=06778001',
    'NV2A read addr=fd400984 value=84000000',
    '[AV] query AV pack=00400104',
    'PFIFO bind sub=0 handle=0000000d instance=000149c0 class=97',
    'PFIFO bind sub=1 handle=0000000e instance=00014cf0 class=39',
    'PFIFO bind sub=2 handle=00000010 instance=00014d00 class=9f',
    'PFIFO bind sub=3 handle=00000011 instance=00014d10 class=62',
    'PFIFO bind sub=5 handle=00000012 instance=00014d20 class=44',
    'NV2A context interrupt addr=06675004 value=00000000',
    'PGRAPH semaphore physical=06674000 value=00000005',
    'PFIFO executed start=06675000 GET=PUT=06675280 packets=32 arguments=128',
    '[D3D] CreateDevice returned HRESULT=00000000',
    'NV2A USER write addr=fd800040 value=06675ad4',
    'PGRAPH clear depth base=06a48000 pitch=3072 rect=0,0..720,480 value=ffffff00 mask=ffffffff',
    'PGRAPH clear color base=06778000 pitch=3072 rect=0,0..720,480 value=00000000 mask=ffffffff',
    'PFIFO executed start=06675280 GET=PUT=06675ad4 packets=200 arguments=333',
    'scanout captured physical=06778000 size=720x480 pitch=3072 nonblack=0',
    'NV2A write addr=fd600800 value=06778000',
    '[AV] encoder field=', '[AV] screen blank=0',
    r'open path=d:\load_img.bin root=fffffffd access=80100080 disposition=1 options=00000060 status=00000000',
    'requested=37596 transferred=37596 status=00000000',
    '[KERNEL] 23 ExQueryPoolBlockSize',
    'AC97 codec ready', '[IRQ] connected bus=6', '[IRQ] connected bus=5',
    'APU voice activated in guest RAM', 'requested=15308 transferred=15308 status=00000000',
    'APU GP acknowledged effects image (silent)',
    '[THREAD] started id=2 routine=003298ad target=0033e3e0',
    'requested=73728 transferred=73728 status=00000000',
    'PGRAPH textured strip completed in guest render target',
    '[RESULT] status=1 reason=' + expected_stop,
]
format_markers = [
    'code=00074004 out=32 status=00000000',
    'offset=114688 requested=4096 transferred=4096 status=00000000',
    'code=00090020 out=0 status=00000000',
]

def snapshot(base):
    return {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}

def normalized(files):
    # FATX's volume ID comes from KeQuerySystemTime at each fresh format.
    return {p: b[:4] + bytes(4) + b[8:] if p == 'hdd/cache-partition5.bin' else b
            for p, b in files.items()}

with tempfile.TemporaryDirectory(prefix='ngb-startup-data-') as data:
    run('startup', xbe, 1, startup_markers + format_markers, data=data)
    base = Path(data)
    files = snapshot(base)
    expected = {'TitleMeta.xbx': 64, 'TitleImage.xbx': 10240, 'SaveImage.xbx': 4096,
                'partition0-header.bin': 4096, 'cache-partition5.bin': 118784, 'instinfo.ins': 212}
    assert {Path(p).name: len(b) for p, b in files.items()} == expected, files.keys()
    assert (base / 'hdd/partition5').is_dir()
    cache = files['hdd/cache-partition5.bin']
    assert cache[:4] == b'FATX' and int.from_bytes(cache[8:12], 'little') == 32
    assert int.from_bytes(cache[12:16], 'little') == 1
    assert cache[4096:4100] == bytes.fromhex('f8ffffff')
    assert cache[102400:] == bytes([255]) * 16384
    header = files['hdd/partition0-header.bin']
    assert header[2048:2052] == bytes.fromhex('86523197')
    assert (0x5443000d).to_bytes(4, 'little') in header[2056:2092]
    run('repeat-startup', xbe, 1, startup_markers, format_markers, data=data)
    assert snapshot(base) == files, 'Repeat startup reformatted or accumulated data'
    results.append({'test': 'bounded-persistent-metadata', 'status': 'passed',
                    'files': len(files), 'bytes': sum(map(len, files.values()))})
    install_record = {p:b for p,b in files.items() if p == "hdd/partition5/instinfo.ins"}
    metadata = {p:b for p,b in files.items() if p.startswith('hdd/partition1/')}
    with tempfile.TemporaryDirectory(prefix='ngb-upgrade-') as upgrade:
        base = Path(upgrade)
        captured = out / 'device-logs/20261111-095244/data'
        previous = snapshot(captured) if captured.is_dir() else files
        for path, content in previous.items():
            dest = base / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        run('upgrade-from-0.4.0', xbe, 1, startup_markers, format_markers, data=upgrade)
        assert snapshot(base) == {**install_record, **previous}
    for version, stamp in [('0.5.0', '20261111-100610'), ('0.6.0', '20261111-101904'),
                           ('0.7.0', '20261111-102541'), ('0.8.0', '20261111-103536'),
                           ('0.9.0', '20261111-104508'), ('0.10.0', '20261111-113016'),
                           ('0.11.0', '20261111-114043'), ('0.12.0', '20261111-121516'),
                           ('0.13.0', '20261111-130834'), ('0.16.0', '0.16.0-text')]:
        captured = out / 'device-logs' / stamp / 'data'
        if not captured.is_dir():
            continue
        with tempfile.TemporaryDirectory(prefix='ngb-upgrade-') as upgrade:
            import shutil
            shutil.copytree(captured, upgrade, dirs_exist_ok=True)
            run(f'upgrade-from-{version}', out / 'romfs/default.xbe', 1,
                startup_markers, format_markers, data=upgrade)
            assert snapshot(Path(upgrade)) == {**install_record, **snapshot(captured)}
    run('graphics-command-trace', xbe, 1, startup_markers + [
        '[FIFO-SCAN] from=06675280 to=06675ad4 bytes=2132 packets=200',
        '[FIFO-SCAN] clear argument at=06675a94', '[FIFO-SCAN] clear argument at=06675ab0',
    ], format_markers, data=data, timing='--fifo-trace')
    vblank_log = run('vblank-after-startup-semaphore', xbe, 1, startup_markers,
                     format_markers, data=data, timing='--graphics-vblank')
    pos = 0
    for marker in ['PGRAPH semaphore', '[TEST] vblank after startup semaphore readback=5',
                   'NV2A read8 addr=fd6013d4',
                   'NV2A write addr=fd600100 value=00000001', '[D3D] CreateDevice returned']:
        pos = vblank_log.index(marker, pos) + len(marker)
    # The GPU DPC already servicing the context switch can acknowledge the
    # first vblank itself. Subsequent vblanks still need a working IRQ.
    assert 'pending=1000000 handled=1' in vblank_log
    assert snapshot(Path(data)) == files
    timing_log = run('usb-reset-during-instance-clear', xbe, 1, startup_markers,
                     format_markers, data=data, timing="--usb-reset")
    pos = 0
    for marker in ['PRAMIN write addr=fd710000', 'fire object=0045e7a8',
                   'OHCI0 write offset=54 value=80000010', 'OHCI0 write offset=54 value=00100000',
                   'PRAMIN write addr=fd714ffc', expected_stop]:
        pos = timing_log.index(marker, pos) + len(marker)
    assert snapshot(Path(data)) == files
    slow_log = run('usb-enumeration-before-first-frame', xbe, 1, startup_markers,
                   format_markers, data=data, timing="--usb-slow")
    pos = 0
    for marker in ['OHCI0 write offset=08 value=00000002',
                   'OHCI0 SETUP request=80:06 value=0100 length=8',
                   'OHCI0 published control completion', 'unlock pages va=0045e7dc bytes=8',
                   'OHCI0 SETUP request=00:05 value=0001 length=0',
                   'OHCI0 SETUP request=80:06 value=0200',
                   'OHCI0 SETUP request=00:09 value=0001',
                   'OHCI0 SETUP request=c1:06 value=4200',
                   'scanout captured physical=06778000', expected_stop]:
        pos = slow_log.index(marker, pos) + len(marker)
    assert snapshot(Path(data)) == files
    for name, initial in [
        ('recover-empty-metadata', {'hdd/partition1/UDATA/5443000d/TitleMeta.xbx': b''}),
        ('upgrade-from-0.3.1', metadata),
        ('recover-interrupted-format', {**files, 'hdd/cache-partition5.bin': cache[:4096]}),
        ('recover-invalid-cache-header', {**files, 'hdd/cache-partition5.bin': bytes(4) + cache[4:]}),
    ]:
        with tempfile.TemporaryDirectory(prefix='ngb-recovery-') as recovery:
            base = Path(recovery)
            for path, content in initial.items():
                dest = base / path; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(content)
            log = run(name, xbe, 1, startup_markers + format_markers, data=recovery)
            assert normalized(snapshot(base)) == normalized(files), name
            if name.startswith('recover-interrupted') or name.startswith('recover-invalid'):
                assert 'status=c000014f' in log, 'Unformatted volume was silently accepted'
with tempfile.TemporaryDirectory(prefix='ngb-startup-') as tmp:
    wrong = Path(tmp) / 'wrong.xbe'
    data = bytearray(xbe.read_bytes())
    data[0] ^= 1
    wrong.write_bytes(data)
    run('invalid-image-header', wrong, 2, ['Invalid default.xbe header', '[RESULT] status=2'], ['[ENTER]'])
    wrong.write_bytes(b'XBEH')
    run('truncated-image', wrong, 2, ['Invalid or truncated default.xbe', '[RESULT] status=2'], ['[ENTER]'])
    run('missing-image', Path(tmp) / 'absent.xbe', 2, ['Cannot open default.xbe', '[RESULT] status=2'], ['[ENTER]'])
# Exercise a Start press on Warnings and let the original Sofdec decoder
# submit a frame. Use the Switch RomFS for both a fresh and a warm cache.
with tempfile.TemporaryDirectory(prefix='ngb-movie-') as tmp:
    cache = Path(tmp) / 'hdd/partition5/demo.afs'
    for phase in ('cold', 'warm'):
        name = f'opening-movie-{phase}'
        log_path = out / f'verify-{name}.log'
        env = {**os.environ, 'NGB_FULL_TRACE':'1', 'NGB_TEST_MOVIE_FRAME':'1', 'NGB_TEST_MOVIE_MOTION':'1', 'NGB_TEST_ORIGINAL_MOVIE':'1'}
        env.pop('NGB_TEST_VISIBLE_FRAME', None)
        with log_path.open('w') as log:
            p = subprocess.run([out / 'host/ngb-runtime-test', '--start-button', out / 'romfs', tmp],
                               stdout=log, stderr=subprocess.STDOUT, env=env, timeout=200)
        log = log_path.read_text()
        assert p.returncode == 1 and 'reason=verified visible movie frame' in log, (name, log[-1500:])
        assert log.count('[TEST] early physical Start tap') == 1 and 'Buffered warning Start on guest flip' in log
        fade = re.search(r'Warning fade steps=(\d+) elapsed_ms=(\d+)', log)
        assert fade and int(fade[1]) >= 15 and int(fade[2]) < 4000, (name, fade)
        assert '[TEST] distinct movie scanouts=120 ' in log and 'Movie content changes=120 ' in log
        assert 'First Start report delivered' in log and '[TEST] movie scanout' in log
        assert 'unsupported page protection change' not in log
        if phase == 'cold':
            assert '[MEMORY] protect va=84095900' in log
        assert cache.read_bytes() == (root / 'game_files/demo.afs').read_bytes()
        results.append({'test':name, 'status':'passed', 'exit_code':p.returncode})
# Drive the shipping path from Warnings through the actual program-end packet.
with tempfile.TemporaryDirectory(prefix='ngb-native-movie-') as tmp:
    for phase in ('cold','warm','cancel'):
        name=f'native-opening-{phase}'
        env=os.environ.copy()
        if phase=='cancel':
            env['NGB_TEST_CANCEL_OPENING']='1'
        else:
            env['NGB_TEST_TITLE_MENU']='1'
            env['NGB_FULL_TRACE']='1'
        log_path=out/f'verify-{name}.log'
        with log_path.open('w') as output:
            p=subprocess.run([out/'host/ngb-runtime-test','--start-button',out/'romfs',tmp],
                    stdout=output,stderr=subprocess.STDOUT,env=env,timeout=90)
        log=log_path.read_text()
        assert '[TEST] early physical Start tap' in log and 'Opening movie frame=1 ' in log
        assert log.count('Opening movie native playback during guest prep') == 1
        latency=re.search(r'Opening movie startup start_to_frame_ms=(-?\d+) select_to_frame_ms=(\d+)',log)
        assert latency and 0<=int(latency[2])<=int(latency[1]), (name,latency)
        if phase=='cancel':
            assert p.returncode==3 and 'Opening movie cancelled frames=10 ' in log and 'cancel requested' in log
        else:
            eof=re.search(r'Opening movie EOF frames=600 elapsed_ms=(\d+)',log)
            motion=re.search(r'opening display frames=600 changes=(\d+)',log)
            assert eof and 19980<=int(eof[1])<22000 and motion and int(motion[1])>400, (name,log[-2400:])
            assert 'Opening movie guest teardown' in log[eof.end():], (name,log[-2400:])
            assert p.returncode == 1 and '[TEST] visible original title logo' in log
            assert 'Main menu overlay renderer=' in log and 'overlay renderer=CPU' not in log
            assert '[TEST] visible original main menu' in log and 'reason=verified navigable main menu' in log
            initial=re.search(r'Main menu entry first_30_flips_ms=(\d+)',log)
            assert initial and int(initial[1]) > 0, (name,initial)
            response=re.search(r'Main menu direction_to_flip_ms=(\d+) cursor=[1-7]',log)
            assert response and int(response[1]) < 500, (name,response)
            saves=list(Path(tmp).rglob('system.dat'))
            assert len(saves)==1 and saves[0].stat().st_size==1360, (name,saves)
            if phase=='warm':
                # The game reads its existing system data, then signs and rewrites
                # it. Match the original read handle before the opening plays.
                before_movie=log[:log.index('Opening movie native playback')]
                opened=re.search(r'open path=T:\\system\.dat .*?status=00000000 handle=(\w+)',before_movie)
                assert opened and f'read handle={opened[1]} offset=-2 requested=1360 transferred=1360 status=00000000' in before_movie
        results.append({'test':name,'status':'passed','exit_code':p.returncode})
(out / 'verification.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
