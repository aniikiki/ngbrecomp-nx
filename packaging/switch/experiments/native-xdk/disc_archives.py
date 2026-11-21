"""Link the title's disc archive routing into the player and its ARM replay."""
import re
import subprocess


def link_disc_archives(root, output, link):
    source = root / 'packaging/switch/runtime/direct/disc_archives.S'
    addresses = re.findall(r'^archive_entry ([0-9A-F]{8})\b', source.read_text(), re.MULTILINE)
    assert addresses and len(addresses) == len(set(addresses))
    obj = output / 'disc_archives.o'
    subprocess.run([link[0], '-c', str(source), '-o', str(obj)], check=True)
    entries = ['ngb_reg_sub_' + address for address in addresses]
    link[1:1] = [str(obj)] + ['-Wl,--wrap=' + name for name in entries]
    return ['__wrap_' + name for name in entries]
