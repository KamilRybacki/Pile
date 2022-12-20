import subprocess
import sys

DEFAULT_NUMBER_OF_DISKS = 4
DEFAULT_DISK_SIZE = '1M'
DEFAULT_HOSTS_FILE_PATH = "/hosts.yml"

def cleanup_loop_devices() -> None:
    def decode_loop_device_paths(paths: subprocess.CompletedProcess[bytes]) -> list[str]:
        return paths.stdout.decode().strip().split("\n")

    loop_devices_list_bytes: subprocess.CompletedProcess[bytes] = subprocess.run(["sudo", "losetup", "-a"], capture_output=True, check=True)
    loop_devices = [
        line.split(":")[0]
        for line in decode_loop_device_paths(loop_devices_list_bytes)
    ]
    for loop_device in loop_devices:
        subprocess.run(["sudo", "losetup", "-d", loop_device], check=True)

def get_loop_devices_setup_config(arguments: list[str]) -> tuple[int, str]:
    if len(arguments) == 1:
        return DEFAULT_NUMBER_OF_DISKS, DEFAULT_DISK_SIZE
    if len(arguments) == 2:
        return int(arguments[1]), DEFAULT_DISK_SIZE
    if len(arguments) == 3:
        return int(arguments[1]), arguments[2]

    n_disks: int = int(arguments[0]) if len(sys.argv) > 1 else DEFAULT_NUMBER_OF_DISKS
    size: str = arguments[1] if len(sys.argv) > 2 else DEFAULT_DISK_SIZE

    if n_disks < 1:
        raise ValueError("You must provide a number of disks greater than 0")
    if size[-1] not in ['M', 'G', 'T']:
        raise ValueError("You must provide a disk size with a unit of measure: M, G, T")
    if size[-1] == 'T':
        raise ValueError("You must provide a disk size less than 1T")
    if not size[:-1].isnumeric():
        raise ValueError("You must provide a disk size with a numeric value")
    if int(size[:-1]) < 1:
        raise ValueError("You must provide a disk size greater than 0")

    return n_disks, size

def setup_dummy_disks(number_of_disks_to_setup: int, disk_size: str) -> list[str]:
    loop_devices = [setup_dummy_disk(i, disk_size) for i in range(number_of_disks_to_setup)]
    for loop_device in loop_devices:
        subprocess.run(["sudo", "mkfs.ext4", loop_device], check=True)
    return loop_devices

def setup_dummy_disk(index: int, size: str) -> str:
    loop_device_source: str = f"loop_device{index}.img"
    loop_device_path: str = f"/dev/loop{index}"
    subprocess.run(['truncate', '-s', size, loop_device_source], check=True)
    subprocess.run(["sudo", "losetup", loop_device_path, loop_device_source], check=True)
    return loop_device_path

def write_inventory_file_for_ansible(devices: list[str], path: str) -> None:
    with open(path, "w", encoding='utf-8') as inventory_file:
        inventory_file.write("""
        pilehost:
            hosts:
                pile:
                    ansible_host: 127.0.0.1
                    ansible_connection: local
                    ansible_python_interpreter: /usr/bin/python3
                    pile_username: test
                    pile_group: test
                    pile_vg_name: testvg
                    disks:
        """)
        for device in devices:
            inventory_file.write(f"\t\t\t\t - {device}")
        inventory_file.write("\t\t\t s3_combined_volume: /mnt/data")

if __name__ == "__main__":
    if len(sys.argv) < 1:
        raise ValueError("You must provide a command: setup or cleanup")
    if sys.argv[0] == "cleanup":
        cleanup_loop_devices()
    if sys.argv[0] == "setup":
        number_of_disks, input_disk_size = get_loop_devices_setup_config(sys.argv[1:])
        disks = setup_dummy_disks(number_of_disks, input_disk_size)
        output_file_path: str = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_HOSTS_FILE_PATH
        write_inventory_file_for_ansible(disks, output_file_path)
