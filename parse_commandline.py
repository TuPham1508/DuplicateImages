__author__ = 'lene'

from argparse import ArgumentParser, Namespace


def parse_command_line() -> Namespace:
    parser = ArgumentParser(description="Find pairs of equal or similar images.")

    parser.add_argument(
        'root_directory', default='.',
        help="The root of the directory tree under which images are compared"
    )
    parser.add_argument(
        '--fuzziness', '-f', default=0.001, type=float,
        help="Maximum deviation (RMS) of the histograms of two images still considered equal"
    )
    parser.add_argument(
        '--aspect-fuzziness', default=0.05, type=float,
        help="Maximum difference in aspect ratios of two images to compare more closely"
    )
    parser.add_argument(
        '--comparison-method', choices=['compare_exactly', 'compare_histograms'],
        default='compare_exactly',
        help="Method used to determine if two images are considered equal"
    )
    parser.add_argument(
        '--action-equal', choices=('delete_first', 'delete_second', 'view', 'none'),
        default='view', help="command to be run on each pair of images found to be equal"
    )
    parser.add_argument(
        '--parallel', action='store_true', help="Filter using all available cores (Experimental)"
    )
    parser.add_argument('--chunk-size', type=int, help="Chunk size for parallelization")

    return parser.parse_args()
