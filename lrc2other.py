import os
import sys
import re
import time
import uuid
import argparse


def parse_lrc_line(line):
    try:
        ret = re.search(r"^\s*\[(\d+):(\d+\.\d+)\](.*)$", line)
        minute = int(ret.group(1))
        second = float(ret.group(2))
        text = ret.group(3)
        return [minute, second, text]
    except:
        return []


def add_second(group, second):
    t = 0.0 + group[0]*60 + group[1]
    t += second
    return [t//60, t % 60, group[2]]


def format_srt_time(minute, second):
    return "{:02d}:{:02d}:{:02d},{:03d}".format(int(minute//60), int(minute % 60), int(second // 1), int((second % 1)*1000))


def read_lrc(lines):
    groups = list(map(parse_lrc_line, lines))  # 解析每一行为[min, sec, text]
    groups = list(filter(lambda x: len(x) > 0, groups))  # 过滤非法行
    if len(groups) == 0:
        print("歌词不存在有效行！")
        exit(1)

    # 最后仍然存在歌词，补充一个10秒后的空白结尾
    if groups[-1][-1].strip() != '':
        end = add_second(groups[-1], 10.0)
        end[-1] = ""
        groups.append(end)

    out = []
    for i in range(len(groups) - 1):
        # [ startime, end_time, text] , time=[min, second]
        out.append([groups[i][0:2], groups[i+1][0:2], groups[i][2].strip()])
    out = list(filter(lambda x: len(x[2]) > 0, out))
    return out


def format_to_srt(groups):
    out = ""
    index = 1
    for group in groups:
        out += str(index) + "\n"
        out += "{} --> {}\n".format(format_srt_time(*
                                    group[0]), format_srt_time(*group[1]))
        out += group[2] + "\n"
        index += 1
    return out


fcpxml_prefix = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>

<fcpxml version="1.8">
  <resources>
    <format id="r1" name="FFVideoFormat1080p30" frameDuration="{0[0]:.0f}/{0[1]:.0f}s" width="1920" height="1080" colorSpace="1-1-1 (Rec. 709)"/>
    <effect id="r2" name="自定" uid=".../Titles.localized/Build In:Out.localized/Custom.localized/Custom.moti"/>
  </resources>
  <library location="file:///Users/wu/Movies/365days.fcpbundle/">
    <event name="crossub" uid="9BC389E8-726D-4F37-B274-671F36300264">
      <project name="{1}" uid="{2}" modDate="{3}">
        <sequence duration="{4[0]:d}/{4[1]:d}s" format="r1" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
          <spine>
            <gap name="空隙" offset="0s" duration="{4[0]:d}/{4[1]:d}s">
"""

fcpxml_suffix = """
           </gap>
          </spine>
        </sequence>
      </project>
    </event>
    <smart-collection name="项目" match="all">
      <match-clip rule="is" type="project"/>
    </smart-collection>
    <smart-collection name="所有视频" match="any">
      <match-media rule="is" type="videoOnly"/>
      <match-media rule="is" type="videoWithAudio"/>
    </smart-collection>
    <smart-collection name="仅音频" match="all">
      <match-media rule="is" type="audioOnly"/>
    </smart-collection>
    <smart-collection name="静止图像" match="all">
      <match-media rule="is" type="stills"/>
    </smart-collection>
    <smart-collection name="个人收藏" match="all">
      <match-ratings value="favorites"/>
    </smart-collection>
  </library>
</fcpxml>
"""

fcpxml_oneline = """
<title name="{3} - 字幕" lane="1" offset="{0[0]:d}/{0[1]:d}s" ref="r2" duration="{1[0]:d}/{1[1]:}s">
<param name="位置" key="9999/10199/10201/1/100/101" value="0 {2:d}"/>
<param name="对齐" key="9999/10199/10201/2/354/1002961760/401" value="1 (居中)"/>
<param name="Out Sequencing" key="9999/10199/10201/4/10233/201/202" value="0 (到)"/>
<text>
  <text-style ref="ts{4:d}">{3}</text-style>
</text>
<text-style-def id="ts{4:d}">
  <text-style font="PingFang SC" fontSize="62" fontFace="Semibold" fontColor="1 1 1 1" bold="1" strokeColor="0.329705 0.329721 0.329713 1" strokeWidth="1" shadowColor="0 0 0 0.75" shadowOffset="3 315" kerning="1.24" alignment="center"/>
</text-style-def>
</title>
"""

# 帧数对应xml中frameDuration的参数
frame_duration_map = {30: [100, 3000], 60: [100, 6000], 24: [100, 2400]}

def round_frame(frame):
    s = round(frame/100)
    return s * 100

def format_to_fcpxml(groups, filename, y, fps):
    out = ""
    if y == None:
        y = -450
    if fps == None:
        fps = 30

    if not (fps in frame_duration_map):
        print("fps only support 24,30,60 or you need modify this script by yourself.")

    frame_duration = frame_duration_map[fps]
    project_name = time.strftime("%H.%M.%S", time.localtime()) + "_" + filename
    uuid_str = str(uuid.uuid4()).upper()
    mod_date = time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime())
    duration_sec = int(groups[-1][1][1]+1) + 60 * int(groups[-1][1][0])
    duration = [duration_sec * frame_duration[1], frame_duration[1]]
    out += fcpxml_prefix.format(frame_duration,
                                project_name, uuid_str, mod_date, duration)
    index = 1
    for group in groups:
        start_sec = int((group[0][0] * 60 + group[0][1]) * frame_duration[1])
        end_sec = int((group[1][0] * 60 + group[1][1]) * frame_duration[1])
        start_sec = round_frame(start_sec)
        end_sec = round_frame(end_sec)
        out += fcpxml_oneline.format([start_sec, frame_duration[1]],
                                     [end_sec - start_sec, frame_duration[1]], y, group[2], index)
        index += 1

    out += fcpxml_suffix
    return out

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="input LRC file", required=True)
    parser.add_argument(
        "-t", "--type", choices=["srt", "fcpxml"], help="output file type", required=True)
    parser.add_argument(
        "-y", type=int, help="for fcpxml, the verticle offset from the center")
    parser.add_argument(
        "-fps", type=int, help="for fcpxml, you must specific the fps of video")
    parser.add_argument("output", help="output file")
    args = parser.parse_args()
    input_file = open(args.input, "r")
    output_filename = args.output
    if not (output_filename.endswith("." + args.type) or output_filename.endswith("." + args.type.upper())):
        output_filename += "." + args.type
    output_file = open(output_filename, "w")

    lines = input_file.readlines()
    groups = read_lrc(lines)
    out_type = args.type
    y_offset = args.y
    fps = args.fps
    if out_type == "srt":
        out = format_to_srt(groups)
        output_file.write(out)
        output_file.close()
    else:
        out = format_to_fcpxml(groups, args.input, y_offset, fps)
        output_file.write(out)
        output_file.close()

    print(output_filename, "DONE")
