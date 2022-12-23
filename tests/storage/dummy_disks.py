import logging
import subprocess
import sys

DEFAULT_NUMBER_OF_DISKS = 4
DEFAULT_DISK_SIZE = '1M'
DEFAULT_HOSTS_FILE_PATH = "hosts.yml"

DISKS_SETUP_LOG = logging.getLogger("DISKS")


def get_setup_config(arguments: list[str]) -> dict:
    if not arguments:
        raise ValueError("You must provide a command: setup or cleanup")

    cmd: str = arguments[0]
    if cmd not in ["setup", "cleanup"]:
        DISKS_SETUP_LOG.error(f'Invalid command {cmd}. Available commands: setup, cleanup')
        sys.exit(1)

    n_disks: int = int(arguments[1]) if len(arguments) > 1 else DEFAULT_NUMBER_OF_DISKS
    size: str = arguments[2] if len(arguments) > 2 else DEFAULT_DISK_SIZE

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

    path: str = arguments[3] if len(arguments) > 3 else DEFAULT_HOSTS_FILE_PATH

    try:
        with open(path, "w", encoding='utf-8'):
            pass
    except OSError as exception:
        raise OSError(f"Invalid output file path: {path}") from exception

    return {
        'command': cmd,
        'number_of_disks': n_disks,
        'disk_size': size,
        'output_file_path': path
    }


def setup_dummy_disks(number_of_disks_to_setup: int, disk_size: str) -> list[str]:
    DISKS_SETUP_LOG.debug(f"Setting up {number_of_disks_to_setup} disks of size {disk_size}")
    current_loop_devices_list_bytes: subprocess.CompletedProcess[bytes] = subprocess.run(["sudo", "losetup", "-a"], capture_output=True, check=True)
    current_loop_devices_list: list[str] = [
        line.split(":")[0]
        for line in decode_loop_device_paths(current_loop_devices_list_bytes)
    ]
    last_loop_device_created_by_system_index = int(current_loop_devices_list[-1].split("/")[-1].replace("loop", ""))
    new_loop_devices_indices = range(last_loop_device_created_by_system_index, last_loop_device_created_by_system_index + number_of_disks_to_setup)
    loop_devices = [setup_dummy_disk(i, disk_size) for i in new_loop_devices_indices]
    if not loop_devices:
        raise RuntimeError("No disks were created!")

    DISKS_SETUP_LOG.debug(f"Created the following {len(loop_devices)} disks:")
    DISKS_SETUP_LOG.debug(loop_devices)
    return loop_devices


def setup_dummy_disk(index: int, size: str) -> str:
    loop_device_source: str = f"loop_device{index}.img"
    subprocess.run(['truncate', '-s', size, loop_device_source], check=True)

    loop_device_path_bytes: subprocess.CompletedProcess[bytes] = subprocess.run(["sudo", "losetup", "-f"], capture_output=True, check=True)
    loop_device_path: str = loop_device_path_bytes.stdout.decode().strip()
    DISKS_SETUP_LOG.debug(f"Creating {loop_device_source} of size {size} and mounting it on {loop_device_path}")

    subprocess.run(["sudo", "losetup", loop_device_path, loop_device_source], check=True)
    return loop_device_path


def write_inventory_file_for_ansible(devices: list[str], path: str) -> None:
    DISKS_SETUP_LOG.debug(f"Writing inventory file to {path}")
    with open(path, "w", encoding='utf-8') as inventory_file:
        inventory_file.write("pilehost:\n")
        inventory_file.write("    hosts\n")
        inventory_file.write("        pile:")
        inventory_file.write("            ansible_host: 127.0.0.\n")
        inventory_file.write("            ansible_connection: local")
        inventory_file.write("            ansible_python_interpreter: /usr/bin/python\n")
        inventory_file.write("            pile_username: tes\n")
        inventory_file.write("            pile_group: tes\n")
        inventory_file.write("            pile_vg_name: testv\n")
        inventory_file.write("            disks:\n")
        for device in devices:
            inventory_file.write(f"                - {device}\n")
        inventory_file.write("            s3_combined_volume: /mnt/data\n")


def cleanup_loop_devices() -> None:
    loop_devices_list_bytes: subprocess.CompletedProcess[bytes] = subprocess.run(["sudo", "losetup", "-a"], capture_output=True, check=True)
    loop_devices = [
        line.split(":")[0]
        for line in decode_loop_device_paths(loop_devices_list_bytes)
    ]
    for loop_device in loop_devices:
        DISKS_SETUP_LOG.debug(f"Cleaning up {loop_device}")
        subprocess.run(["sudo", "losetup", "-d", loop_device], check=True)


def decode_loop_device_paths(paths: subprocess.CompletedProcess[bytes]) -> list[str]:
    return paths.stdout.decode().strip().split("\n")


if __name__ == "__main__":
    setup_config = get_setup_config(sys.argv[1:])
    if setup_config['command'] == "cleanup":
        cleanup_loop_devices()
    if setup_config['command'] == "setup":
        disks = setup_dummy_disks(setup_config['number_of_disks'], setup_config['disk_size'])  # type: ignore
        write_inventory_file_for_ansible(disks, setup_config['output_file_path'])
