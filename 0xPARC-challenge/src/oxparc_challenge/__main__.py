import argparse
from .release import verify_release,check_manifest

def main():
    parser=argparse.ArgumentParser(description='0xPARC response verification')
    parser.add_argument('command',choices=['verify-release','check-manifest'])
    args=parser.parse_args()
    return verify_release() if args.command=='verify-release' else check_manifest()

if __name__=='__main__':raise SystemExit(main())
