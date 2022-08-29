import logging

from rich.console import Console
from rich.logging import RichHandler

import util
from drive import TeamDrive

td = TeamDrive("client_secrets.json")

console = Console()
LOGGER = logging.getLogger("TeamDrive")
LOGGER.setLevel(logging.WARN)
LOGGER.addHandler(RichHandler())

EXCLUDE_DRIVE_IDS = [
    "exclude1",
    "exclude2",
]


DESTINATIONS = {
    "dst1_name": "dst1_id",
    "dst2_name": "id2_id",
}

search = console.input("Search for folders: ")

imdb = console.input("use imdb to find alternate titles?(y/n): ")
if imdb == "y":
    alt_titles = util.find_alternate_title(search)
    console.print("Alternate titles:")
    for title in alt_titles:
        console.print(f"- {title}")
    query = td.folder_query_builder(queries=alt_titles)

else:
    console.print("not using imdb")
    query = td.folder_query_builder(queries=[search])


with console.status("Searching for folders...") as status:
    while True:
        files = td.list_files(query)
        if len(files) > 0:
            console.print("\n")
            break
        else:
            status.text = "No folders found"
            break

# remove excluded drives
# TODO: should be done in the query builder to minimize the number of files in the first place
files = [file for file in files if file["driveId"] not in EXCLUDE_DRIVE_IDS]

console.print(f"Found {len(files)} folders")
for i, file in enumerate(files):
    console.print(f"{i+1}. Name: {file.get('name')}")
    console.print(f"    Drive Name: {file.get('driveName')}")
    console.print(f"    Parent Names: {file.get('parentNames')}")
    console.print("")
index = console.input(f"\nSelect a folder to copy to: ")
index = int(index) - 1
src_id = files[index]["id"]
src_name = files[index]["name"]

console.print(f"\nSelect a destination folder: ")
for i, dst in enumerate(DESTINATIONS):
    console.print(f"{i+1}. {dst}")

index = console.input(f"\nSelect a destination folder: ")
index = int(index) - 1
dst_id = DESTINATIONS[list(DESTINATIONS.keys())[index]]
dst_name = list(DESTINATIONS.keys())[index]

# confimation
console.print(f"\nCopy {src_name} to {dst_name}?")
confirm = console.input("y/n: ")
if confirm == "n":
    console.print("\nExiting...")
    exit()
else:
    console.print(f"\nCopying {src_name} to {dst_name}")
    with console.status("Copying...") as status:
        td.copy_folder(src_id, src_name=src_name, dst=dst_id)
        status.text = "Copied"
    console.print(f"\n{src_name} copied to {dst_name}")
