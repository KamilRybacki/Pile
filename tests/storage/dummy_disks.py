import subprocess
import sys

DEFAULT_NUMBER_OF_DISKS = 4

def setup_dummy_disk(index: int) -> str:
    subprocess.run(["dd", "if=/dev/zero", f"of=loop_device{index}.img", "bs=1M", "count=1024"], check=True)
    subprocess.run(["sudo", "losetup", "-f", f"loop_device{index}.img"], check=True)
    loop_device_stdout = subprocess.run(["sudo", "losetup", "-a"], capture_output=True, check=True).stdout
    return loop_device_stdout.decode().strip().split(":")[0]

def setup_dummy_disks(number_of_disks_to_setup: int) -> list[str]:
    loop_devices = [setup_dummy_disk(i) for i in range(number_of_disks_to_setup)]
    for loop_device in loop_devices:
        subprocess.run(["sudo", "mkfs.ext4", loop_device], check=True)
    return loop_devices

def write_inventory_file_for_ansible(devices: list[str]) -> None:
    with open("/hosts.yml", "w", encoding='utf-8') as inventory_file:
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

def cleanup_loop_devices() -> None:
    output = subprocess.run(["sudo", "losetup", "-a"], capture_output=True, check=True)
    loop_devices = [
        line.split(":")[0]
        for line in output.stdout.decode().strip().split("\n")
    ]
    for loop_device in loop_devices:
        subprocess.run(["sudo", "losetup", "-d", loop_device], check=True)

if __name__ == "__main__":
    if len(sys.argv) < 1:
        raise ValueError("You must provide a command: setup or cleanup")
    if sys.argv[0] == "cleanup":
        cleanup_loop_devices()
    if sys.argv[0] == "setup":
        number_of_disks: int = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NUMBER_OF_DISKS
        if number_of_disks < 1:
            raise ValueError("You must provide a number of disks greater than 0")
        disks = setup_dummy_disks(number_of_disks)
        write_inventory_file_for_ansible(disks)
