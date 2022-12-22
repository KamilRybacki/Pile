import logging
import subprocess
import sys

DEFAULT_NUMBER_OF_DISKS = 4
DEFAULT_DISK_SIZE = '1M'
DEFAULT_HOSTS_FILE_PATH = "/hosts.yml"

DISKS_SETUP_LOG = logging.getLogger("DISKS")


def cleanup_loop_devices() -> None:
    def decode_loop_device_paths(paths: subprocess.CompletedProcess[bytes]) -> list[str]:
        return paths.stdout.decode().strip().split("\n")

    loop_devices_list_bytes: subprocess.CompletedProcess[bytes] = subprocess.run(["sudo", "losetup", "-a"], capture_output=True, check=True)
    loop_devices = [
        line.split(":")[0]
        for line in decode_loop_device_paths(loop_devices_list_bytes)
    ]
    for loop_device in loop_devices:
        DISKS_SETUP_LOG.debug(f"Cleaning up {loop_device}")
        subprocess.run(["sudo", "losetup", "-d", loop_device], check=True)


def get_loop_devices_setup_config(arguments: list[str]) -> tuple[int | None, str | None]:
    n_disks: int | None = int(arguments[0]) if arguments else DEFAULT_NUMBER_OF_DISKS
    size: str | None = arguments[1] if len(arguments) > 1 else DEFAULT_DISK_SIZE

    if n_disks < 1:  # type: ignore
        DISKS_SETUP_LOG.error("You must provide a number of disks greater than 0")
        n_disks = None
    if size[-1] not in ['M', 'G', 'T']:  # type: ignore
        DISKS_SETUP_LOG.error("You must provide a disk size with a unit of measure: M, G, T")
        size = None
    if size[-1] == 'T':  # type: ignore
        DISKS_SETUP_LOG.error("You must provide a disk size less than 1T")
        size = None
    if not size[:-1].isnumeric():  # type: ignore
        DISKS_SETUP_LOG.error("You must provide a disk size with a numeric value")
        size = None
    if int(size[:-1]) < 1:  # type: ignore
        DISKS_SETUP_LOG.error("You must provide a disk size greater than 0")
        size = None
    return n_disks, size


def setup_dummy_disks(number_of_disks_to_setup: int, disk_size: str) -> list[str]:
    DISKS_SETUP_LOG.debug(f"Setting up {number_of_disks_to_setup} disks of size {disk_size}")
    loop_devices = [setup_dummy_disk(i, disk_size) for i in range(number_of_disks_to_setup)]
    for loop_device in loop_devices:
        DISKS_SETUP_LOG.debug(f"Creating ext4 filesystem on {loop_device}")
        subprocess.run(["sudo", "mkfs.ext4", loop_device], check=True)
    DISKS_SETUP_LOG.debug(f"Created the following {len(loop_devices)} disks:")
    DISKS_SETUP_LOG.debug(loop_devices)
    return loop_devices


def setup_dummy_disk(index: int, size: str) -> str:
    loop_device_source: str = f"loop_device{index}.img"
    loop_device_path: str = f"/dev/loop{index}"
    DISKS_SETUP_LOG.debug(f"Creating {loop_device_source} of size {size} and mounting it on {loop_device_path}")
    subprocess.run(['truncate', '-s', size, loop_device_source], check=True)
    subprocess.run(["sudo", "losetup", loop_device_path, loop_device_source], check=True)
    return loop_device_path


def write_inventory_file_for_ansible(devices: list[str], path: str) -> None:
    DISKS_SETUP_LOG.debug(f"Writing inventory file to {path}")
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
    disks_setup_arguments = sys.argv[1:]
    if len(disks_setup_arguments) < 1:
        raise ValueError("You must provide a command: setup or cleanup")

    if disks_setup_arguments[0] == "cleanup":
        cleanup_loop_devices()
        sys.exit(0)
    if disks_setup_arguments[0] == "setup":
        number_of_disks, input_disk_size = get_loop_devices_setup_config(disks_setup_arguments[1:])
        if number_of_disks is None or input_disk_size is None:
            DISKS_SETUP_LOG.error("Invalid arguments! Exiting...")
            sys.exit(1)
    if disks_setup_arguments[0] not in ["setup", "cleanup"]:
        DISKS_SETUP_LOG.error(f'Invalid command {sys.argv[0]}. Available commands: setup, cleanup')
        sys.exit(1)

    disks = setup_dummy_disks(number_of_disks, input_disk_size)  # type: ignore
    if len(disks) == 0:
        DISKS_SETUP_LOG.error("No disks were created! Exiting...")
        sys.exit(1)

    output_file_path: str = disks_setup_arguments[3] if len(disks_setup_arguments) > 3 else DEFAULT_HOSTS_FILE_PATH
    try:
        with open(output_file_path, "w", encoding='utf-8'):
            pass
    except OSError:
        DISKS_SETUP_LOG.error("Invalid output file path! Exiting...")
        sys.exit(1)

    write_inventory_file_for_ansible(disks, output_file_path)
