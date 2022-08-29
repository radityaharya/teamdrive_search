import re
from imdb import Cinemagoer


imdb = Cinemagoer()
def find_alternate_title(title):
    queries = []
    queries.append(title)
    queries.append(title.replace(" ", "."))
    queries.append(title.replace(" ", "_"))
    queries.append(title.replace(" ", "-"))
    movies = imdb.search_movie(title)
    for i in range(len(movies)):
        movie = movies[i]
        title = movie.get("title")
        queries.append(title.replace(" ", "."))
        queries.append(title.replace(" ", "_"))
        queries.append(title.replace(" ", "-"))
        if i == 5:
            break
    queries = list(set(queries))
    return queries


def result_cleaner(list_folders):
    regex = r"S\d\dE\d\d"
    print("removing season/episode folder")
    list_folders = [x for x in list_folders if not re.search(regex, x["name"])]

    print("removing identified non video folder")
    list_folders = [x for x in list_folders if not "(digital)" in x["name"]]

    return list_folders


def clean_name(name):
    if "[" in name:
        name = name[: name.find("[")] + name[name.find("]") + 1 :]
        if "[" in name:
            name = clean_name(name)
        return name
    else:
        return format_name(name)


def clean_name2(name):
    if "(" in name:
        name = name[: name.find(")")] + name[name.find(")") + 1 :]
        if "(" in name:
            name = clean_name(name)
        return name
    else:
        return name


def replace_multiple_spaces(name):
    name = re.sub(r"\s+", " ", name)
    name = name.strip()
    return name


def format_name(name):
    name = name.replace("-", "_")
    name = name.replace(" ", "_")

    name = name.lower()

    blacklisted_words = [
        "webrip",
        "blueray",
        "regraded",
        "web dl",
        "rarbg",
        "1080p",
        "720p",
        "AMZN",
        "WEB_DL",
        "web_rip",
    ]
    for word in blacklisted_words:
        if word in name:
            name = name.replace(word, "")

    return replace_multiple_spaces(clean_name2(name))