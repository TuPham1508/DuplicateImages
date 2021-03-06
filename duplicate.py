#!/usr/bin/env /usr/bin/python3

import os
from functools import lru_cache, partial
from hashlib import md5
from math import sqrt
from multiprocessing.dummy import Pool
from subprocess import call
from typing import Any, Callable, Dict, Iterator, List, Tuple

from image_wrapper import ImageWrapper, aspects_roughly_equal
from parse_commandline import parse_command_line

CHUNK_SIZE = 25


def files_in_dir(dir_name: str, is_file: Callable=os.path.isfile) -> List[str]:
    """Returns a list of all files in directory dir_name, recursively scanning subdirectories"""
    def files_in_path(path: str) -> List[str]:
        return files_in_dir(path) if os.path.isdir(path) else [path] if is_file(path) else []

    def convoluted_files_in_dir(dir_name: str) -> List[List[str]]:
        return [files_in_path(os.path.join(dir_name, path)) for path in os.listdir(dir_name)]

    return sum(convoluted_files_in_dir(dir_name.rstrip('/')), [])


@lru_cache(maxsize=None)
def get_size(file: str) -> int:
    return os.path.getsize(file)


@lru_cache(maxsize=None)
def get_hash(file: str) -> str:
    return md5(open(file, 'rb').read()).hexdigest()


def compare_exactly(file: str, other_file: str, aspect_fuzziness: float, rms_error: float) -> bool:
    """Returns True if file and other_file are exactly equal"""
    return get_size(other_file) == get_size(file) and get_hash(file) == get_hash(other_file)


def compare_image_histograms(
        image: ImageWrapper, other_image: ImageWrapper, aspect_fuzziness: float, rms_error: float
) -> bool:

    def get_deviations(hist: List[float], other_hist: List[float]) -> Iterator:
        return map(lambda a, b: (a - b) ** 2, hist, other_hist)

    if not aspects_roughly_equal(image, other_image, aspect_fuzziness):
        return False

    deviations = get_deviations(image.get_histogram(), other_image.get_histogram())
    rms = sqrt(sum(deviations) / len(image.get_histogram()))
    return rms < rms_error


def compare_histograms(
        file: str, other_file: str, aspect_fuzziness: float, rms_error: float
) -> bool:
    """Returns True if the histograms of file and other_file differ by
       less than rms_error"""
    try:
        return compare_image_histograms(
            ImageWrapper.create(file), ImageWrapper.create(other_file), aspect_fuzziness, rms_error
        )
    except (IOError, TypeError):
        return False


def pool_filter(
        candidates: List[Tuple[str, str]], compare_images: Callable[[str, str, float, float], bool],
        aspect_fuzziness: float, rms_error: float, chunk_size: float
) -> List[Tuple[str, str]]:
    pool = Pool(None)
    return [
        c
        for c, keep in zip(
            candidates,
            pool.starmap(
                partial(compare_images, aspect_fuzziness=aspect_fuzziness, rms_error=rms_error),
                candidates, chunksize=chunk_size
            )
        )
        if keep
    ]


def similar_images(
        files: List[str], compare_images: Callable[[str, str, float, float], bool],
        aspect_fuzziness: float, rms_error: float, parallel: bool=False, chunk_size=CHUNK_SIZE
) -> List[Tuple[str, str]]:
    """Returns all pairs of image files in the list files that are equal
       according to comparison function compare_images"""

    if parallel:
        candidates = [
            (file, other_file)
            for file in files
            for other_file in files[files.index(file) + 1:]
        ]
        return pool_filter(candidates, compare_images, aspect_fuzziness, rms_error, chunk_size)
    else:
        return [
            (file, other_file)
            for file in files
            for other_file in files[files.index(file) + 1:]
            if compare_images(file, other_file, aspect_fuzziness, rms_error)
        ]


COMPARISON_METHODS = {
    'compare_exactly': compare_exactly,
    'compare_histograms': compare_histograms
}

ACTIONS_ON_EQUALITY = {
    'delete_first': lambda pair: os.remove(pair[0]),
    'delete_second': lambda pair: os.remove(pair[1]),
    'view': lambda pair: call(["xv", "-nolim"] + [pic for pic in pair]),
    'none': lambda pair: None
}  # type: Dict[str, Callable[[Tuple], Any]]


if __name__ == '__main__':

    args = parse_command_line()

    comparison_method = COMPARISON_METHODS[args.comparison_method]
    action_equal = ACTIONS_ON_EQUALITY[args.action_equal]

    image_files = sorted(files_in_dir(args.root_directory, ImageWrapper.is_image_file))
    print("{} total files".format(len(image_files)))

    matches = similar_images(
        image_files, comparison_method,
        aspect_fuzziness=args.aspect_fuzziness, rms_error=args.fuzziness,
        parallel=args.parallel, chunk_size=args.chunk_size if args.chunk_size else CHUNK_SIZE
    )

    print("{} matches".format(len(matches)))

    for pair in sorted(matches):
        action_equal(pair)
