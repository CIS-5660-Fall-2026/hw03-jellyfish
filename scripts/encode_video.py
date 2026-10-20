"""Encode the native rendered frames without changing the simulation or watermark."""
from pathlib import Path
import argparse,json,shutil,subprocess
from PIL import Image

def main():
    p=argparse.ArgumentParser();p.add_argument('output_dir');p.add_argument('--ffmpeg');args=p.parse_args()
    root=Path(args.output_dir).resolve();frames=root/'motion_frames';media=root/'media';media.mkdir(exist_ok=True)
    expected=[frames/f'jellyfish.{f:04d}.png' for f in range(37,180,2)]
    assert set(frames.glob('jellyfish.*.png'))==set(expected), 'The frame sequence is incomplete or contains extra frames.'
    for path in expected:
        with Image.open(path) as im:
            assert im.size==(576,720),(path,im.size)
            im.verify()
    ffmpeg=args.ffmpeg or shutil.which('ffmpeg')
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    mp4=media/'jellyfish-animation.mp4';gif=media/'jellyfish-preview.gif'
    subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate','12','-pattern_type','glob','-i',str(frames/'jellyfish.*.png'),
                    '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],check=True)
    filters='fps=8,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3'
    subprocess.run([ffmpeg,'-y','-loglevel','error','-i',str(mp4),'-filter_complex',filters,'-loop','0',str(gif)],check=True)
    import imageio_ffmpeg
    count,seconds=imageio_ffmpeg.count_frames_and_secs(str(mp4))
    assert count==72 and abs(seconds-6)<.1,(count,seconds)
    info={'source_frames':[37,179,2],'video_frames':count,'duration_seconds':seconds,'fps':12,'size':[576,720],
          'renderer':'Houdini Mantra','watermark_preserved':True}
    (root/'video_validation.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps(info,indent=2))
if __name__=='__main__':main()
