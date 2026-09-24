"""Collect latest genuine observations. Run daily after provider/database setup."""
import argparse
import asyncio
import json
from app import providers
from app.price_history import record_snapshot


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True)
    parser.add_argument(
        '--crop',
        choices=['Cotton', 'Wheat', 'Groundnut', 'Rice'],
        required=True
    )
    parser.add_argument('--market', default='')
    args = parser.parse_args()

    feed = await providers.prices(args.crop, args.state, args.market)

    if feed['status'] == 'unavailable':
        print(json.dumps({
            'status': 'unavailable',
            'message': feed['message']
        }))
        return 1

    result = record_snapshot(feed, args.crop, args.state, args.market)
    print(json.dumps(result))

    return 0 if result['status'] == 'recorded' and not result.get('truncated') else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
