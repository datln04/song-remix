import argparse
import os
from remix.pipeline import RemixPipeline, Config


def main():
    p = argparse.ArgumentParser(description="Auto remix covers with aligned lyrics")
    p.add_argument('--song_name', required=True)
    p.add_argument('--lyrics', default=None, help='Path to lyrics file or raw text')
    p.add_argument('--num_covers', type=int, default=5)
    p.add_argument('--model_size', default='small')
    p.add_argument('--out', default='final_remix.mp4')
    p.add_argument('--no_subtitles', action='store_true')
    p.add_argument('--local_videos', nargs='*', help='Optional local video files to use instead of downloading')
    args = p.parse_args()

    lyrics_text = None
    if args.lyrics:
        if os.path.exists(args.lyrics):
            with open(args.lyrics, 'r', encoding='utf-8') as f:
                lyrics_text = f.read()
        else:
            lyrics_text = args.lyrics

    cfg = Config(
        song_name=args.song_name,
        lyrics=lyrics_text,
        num_covers=args.num_covers,
        model_size=args.model_size,
        out_path=args.out,
        add_subtitles=(not args.no_subtitles),
        local_videos=args.local_videos
    )
    pipe = RemixPipeline(cfg)
    out = pipe.run()
    print(f"Exported: {out}")


if __name__ == '__main__':
    main()
