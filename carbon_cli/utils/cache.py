import os
import json


from pathlib import Path


def cache_lookup(key, loader):
    cache_file = str(Path.home() / ".carbon_cli_cache.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
    else:
        cache = {}
    if key in cache:
        return cache[key], True
    result = loader()
    cache[key] = result
    with open(cache_file, "w") as f:
        json.dump(cache, f)
    return result, False


def cache_clear():
    from pathlib import Path

    cache_file = str(Path.home() / ".carbon_cli_cache.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
        return True
    return False
