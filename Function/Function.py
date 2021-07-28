#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import json
from PIL import Image
from configparser import ConfigParser
from Getter import avsox, javbus, javdb, mgstage, dmm, jav321, xcity


# ========================================================================Get config
def get_config():
    config_file = ''
    if os.path.exists('../config.ini'):
        config_file = '../config.ini'
    elif os.path.exists('config.ini'):
        config_file = 'config.ini'
    config = ConfigParser()
    config.read(config_file, encoding='UTF-8')
    return config


# ========================================================================Whether it is uncensored
def is_uncensored(number):
    if re.match('^\d{4,}', number) or re.match('n\d{4}', number) or 'HEYZO' in number.upper():
        return True
    config = get_config()
    prefix_list = str(config['uncensored']['uncensored_prefix']).split('|')
    for pre in prefix_list:
        if pre.upper() in number.upper():
            return True
    return False


# ========================================================================Metadata acquisition failure detection
def getDataState(json_data):
    if json_data['title'] == '' or json_data['title'] == 'None' or json_data['title'] == 'null':
        return 0
    else:
        return 1


# ========================================================================Remove abnormal characters
def escapePath(path, Config):  # Remove escape literals
    escapeLiterals = Config['escape']['literals']
    backslash = '\\'
    for literal in escapeLiterals:
        path = path.replace(backslash + literal, '')
    return path


# ========================================================================Get a list of videos
def movie_lists(escape_folder, movie_type, movie_path):
    if escape_folder != '':
        escape_folder = re.split('[,，]', escape_folder)
    total = []
    file_type = movie_type.split('|')
    file_root = movie_path.replace('\\', '/')
    for root, dirs, files in os.walk(file_root):
        if escape_folder != '':
            flag_escape = 0
            for folder in escape_folder:
                if folder in root:
                    flag_escape = 1
                    break
            if flag_escape == 1:
                continue
        for f in files:
            file_type_current = os.path.splitext(f)[1]
            file_name = os.path.splitext(f)[0]
            if re.search(r'^\..+', file_name):
                continue
            if file_type_current in file_type:
                path = root + '/' + f
                # path = path.replace(file_root, '.')
                path = path.replace("\\\\", "/").replace("\\", "/")
                total.append(path)
    return total


# ========================================================================Get serial number
def getNumber(filepath, escape_string):
    filepath = filepath.replace('-C.', '.').replace('-c.', '.')
    filename = os.path.splitext(filepath.split('/')[-1])[0]
    escape_string_list = re.split('[,，]', escape_string)
    for string in escape_string_list:
        if string in filename:
            filename = filename.replace(string, '')
    part = ''
    if re.search('-CD\d+', filename):
        part = re.findall('-CD\d+', filename)[0]
    if re.search('-cd\d+', filename):
        part = re.findall('-cd\d+', filename)[0]
    filename = filename.replace(part, '')
    filename = str(re.sub("-\d{4}-\d{1,2}-\d{1,2}", "", filename))  # Remove the time in the file name
    filename = str(re.sub("\d{4}-\d{1,2}-\d{1,2}-", "", filename))  # Remove the time in the file name
    if re.search('^\D+\.\d{2}\.\d{2}\.\d{2}', filename):  # Extract European and American numbers sexart.11.11.11
        try:
            file_number = re.search('\D+\.\d{2}\.\d{2}\.\d{2}', filename).group()
            return file_number
        except:
            return os.path.splitext(filepath.split('/')[-1])[0]
    elif re.search('XXX-AV-\d{4,}', filename.upper()):  # 提取xxx-av-11111
        file_number = re.search('XXX-AV-\d{4,}', filename.upper()).group()
        return file_number
    elif '-' in filename or '_' in filename:  # Ordinary extraction number mainly deals with numbers containing minus signs-and _
        if 'FC2' or 'fc2' in filename:
            filename = filename.upper().replace('PPV', '').replace('--', '-')
        if re.search('FC2-\d{5,}', filename):  # Extract similar numbers from fc2-111111
            file_number = re.search('FC2-\d{5,}', filename).group()
        elif re.search('[a-zA-Z]+-\d+', filename):  # Extract similar mkbd-120 number
            file_number = re.search('\w+-\d+', filename).group()
        elif re.search('\d+[a-zA-Z]+-\d+', filename):  # Extract numbers similar to 259luxu-1111
            file_number = re.search('\d+[a-zA-Z]+-\d+', filename).group()
        elif re.search('[a-zA-Z]+-[a-zA-Z]\d+', filename):  # Extract similar mkbd-s120 number
            file_number = re.search('[a-zA-Z]+-[a-zA-Z]\d+', filename).group()
        elif re.search('\d+-[a-zA-Z]+', filename):  # Extract the number similar to 111111-MMMM
            file_number = re.search('\d+-[a-zA-Z]+', filename).group()
        elif re.search('\d+-\d+', filename):  # Extract numbers similar to 111111-000
            file_number = re.search('\d+-\d+', filename).group()
        elif re.search('\d+_\d+', filename):  # Extract numbers similar to 111111_000
            file_number = re.search('\d+_\d+', filename).group()
        else:
            file_number = filename
        return file_number
    else:  # Extract the number without minus sign -, FANZA CID keep ssni00644, change MIDE139 to MIDE-139
        try:
            file_number = os.path.splitext(filename.split('/')[-1])[0]
            find_num = re.findall(r'\d+', file_number)[0]
            find_char = re.findall(r'\D+', file_number)[0]
            if len(find_num) <= 4 and len(find_char) > 1:
                file_number = find_char + '-' + find_num
            return file_number
        except:
            return os.path.splitext(filepath.split('/')[-1])[0]


# ========================================================================Get data according to the serial number
def getDataFromJSON(file_number, config, mode, appoint_url):  # 从JSON returns metadata
    # ================================================Start of adding site rules================================================
    isuncensored = is_uncensored(file_number)
    json_data = {}
    if mode == 1:  # Scraping from all sites
        # =======================================================================Uncoded capture: 111111-111, n1111, HEYZO-1111, SMD-115
        if isuncensored:
            json_data = json.loads(javbus.main_uncensored(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(javdb.main(file_number, appoint_url, True))
            if getDataState(json_data) == 0 and 'HEYZO' in file_number.upper():
                json_data = json.loads(jav321.main(file_number, appoint_url, True))
            if getDataState(json_data) == 0:
                json_data = json.loads(avsox.main(file_number, appoint_url))
        # =======================================================================259LUXU-1111
        elif re.match('\d+[a-zA-Z]+-\d+', file_number) or 'SIRO' in file_number.upper():
            json_data = json.loads(mgstage.main(file_number, appoint_url))
            file_number = re.search('[a-zA-Z]+-\d+', file_number).group()
            if getDataState(json_data) == 0:
                json_data = json.loads(jav321.main(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(javdb.main(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(javbus.main(file_number, appoint_url))
        # =======================================================================FC2-111111
        elif 'FC2' in file_number.upper():
            json_data = json.loads(javdb.main(file_number, appoint_url))
        # =======================================================================ssni00321
        elif re.match('\D{2,}00\d{3,}', file_number) and '-' not in file_number and '_' not in file_number:
            json_data = json.loads(dmm.main(file_number, appoint_url))
        # =======================================================================sexart.15.06.14
        elif re.search('\D+\.\d{2}\.\d{2}\.\d{2}', file_number):
            json_data = json.loads(javdb.main_us(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(javbus.main_us(file_number, appoint_url))
        # =======================================================================MIDE-139
        else:
            json_data = json.loads(javbus.main(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(jav321.main(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(xcity.main(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(javdb.main(file_number, appoint_url))
            if getDataState(json_data) == 0:
                json_data = json.loads(avsox.main(file_number, appoint_url))
    elif re.match('\D{2,}00\d{3,}', file_number) and mode != 7:
        json_data = {
            'title': '',
            'actor': '',
            'website': '',
        }
    elif mode == 2:  # Only from mgstage
        json_data = json.loads(mgstage.main(file_number, appoint_url))
    elif mode == 3:  # Only from javbus
        if isuncensored:
            json_data = json.loads(javbus.main_uncensored(file_number, appoint_url))
        elif re.search('\D+\.\d{2}\.\d{2}\.\d{2}', file_number):
            json_data = json.loads(javbus.main_us(file_number, appoint_url))
        else:
            json_data = json.loads(javbus.main(file_number, appoint_url))
    elif mode == 4:  # Only from jav321
        json_data = json.loads(jav321.main(file_number, isuncensored, appoint_url))
    elif mode == 5:  # Only from javdb
        if re.search('\D+\.\d{2}\.\d{2}\.\d{2}', file_number):
            json_data = json.loads(javdb.main_us(file_number, appoint_url))
        else:
            json_data = json.loads(javdb.main(file_number, appoint_url, isuncensored))
    elif mode == 6:  # Only from avsox
        json_data = json.loads(avsox.main(file_number, appoint_url))
    elif mode == 7:  # Only from xcity
        json_data = json.loads(xcity.main(file_number, appoint_url))
    elif mode == 8:  # Only from dmm
        json_data = json.loads(dmm.main(file_number, appoint_url))

    # ================================================End of site rule addition================================================
    # print(json_data)
    # ======================================Timeout or not found
    if json_data['website'] == 'timeout':
        return json_data
    elif json_data['title'] == '':
        return json_data
    # ======================================Processed information
    title = json_data['title']
    number = json_data['number']
    actor_list = str(json_data['actor']).strip("[ ]").replace("'", '').split(',')  # String to list
    release = json_data['release']
    try:
        cover_small = json_data['cover_small']
    except:
        cover_small = ''
    tag = str(json_data['tag']).strip("[ ]").replace("'", '').replace(" ", '').split(',')  # String to List @
    actor = str(actor_list).strip("[ ]").replace("'", '').replace(" ", '')
    if actor == '':
        actor = 'Unknown'

    # ====================Handling abnormal characters====================== #\/:*?"<>|
    title = title.replace('\\', '')
    title = title.replace('/', '')
    title = title.replace(':', '')
    title = title.replace('*', '')
    title = title.replace('?', '')
    title = title.replace('"', '')
    title = title.replace('<', '')
    title = title.replace('>', '')
    title = title.replace('|', '')
    title = title.replace(' ', '.')
    title = title.replace('【', '')
    title = title.replace('】', '')
    release = release.replace('/', '-')
    tmpArr = cover_small.split(',')
    if len(tmpArr) > 0:
        cover_small = tmpArr[0].strip('\"').strip('\'')
    for key, value in json_data.items():
        if key == 'title' or key == 'studio' or key == 'director' or key == 'series' or key == 'publisher':
            json_data[key] = str(value).replace('/', '')
    # ====================Handling abnormal characters END================== #\/:*?"<>|

    naming_media = config['Name_Rule']['naming_media']
    naming_file = config['Name_Rule']['naming_file']
    folder_name = config['Name_Rule']['folder_name']

    # Return the processed json_data
    json_data['title'] = title
    json_data['number'] = number
    json_data['actor'] = actor
    json_data['release'] = release
    json_data['cover_small'] = cover_small
    json_data['tag'] = tag
    json_data['naming_media'] = naming_media
    json_data['naming_file'] = naming_file
    json_data['folder_name'] = folder_name
    return json_data


# ========================================================================Return the data in json
def get_info(json_data):
    for key, value in json_data.items():
        if value == '' or value == 'N/A':
            json_data[key] = 'unknown'
    title = json_data['title']
    studio = json_data['studio']
    publisher = json_data['publisher']
    year = json_data['year']
    outline = json_data['outline']
    runtime = json_data['runtime']
    director = json_data['director']
    actor_photo = json_data['actor_photo']
    actor = json_data['actor']
    release = json_data['release']
    tag = json_data['tag']
    number = json_data['number']
    cover = json_data['cover']
    website = json_data['website']
    series = json_data['series']
    return title, studio, publisher, year, outline, runtime, director, actor_photo, actor, release, tag, number, cover, website, series


# ========================================================================Save the configuration to config.ini
def save_config(json_config):
    # json_config = json.loads(json_config)
    config_file = ''
    if os.path.exists('../config.ini'):
        config_file = '../config.ini'
    elif os.path.exists('config.ini'):
        config_file = 'config.ini'
    with open(config_file, "wt", encoding='UTF-8') as code:
        print("[common]", file=code)
        print("main_mode = " + str(json_config['main_mode']), file=code)
        print("failed_output_folder = " + json_config['failed_output_folder'], file=code)
        print("success_output_folder = " + json_config['success_output_folder'], file=code)
        print("failed_file_move = " + str(json_config['failed_file_move']), file=code)
        print("soft_link = " + str(json_config['soft_link']), file=code)
        print("show_poster = " + str(json_config['show_poster']), file=code)
        print("website = " + json_config['website'], file=code)
        print("# all or mgstage or fc2club or javbus or jav321 or javdb or avsox or xcity or dmm", file=code)
        print("", file=code)
        print("[proxy]", file=code)
        print("type = " + json_config['type'], file=code)
        print("proxy = " + json_config['proxy'], file=code)
        print("timeout = " + str(json_config['timeout']), file=code)
        print("retry = " + str(json_config['retry']), file=code)
        print("# type: no, http, socks5", file=code)
        print("", file=code)
        print("[Name_Rule]", file=code)
        print("folder_name = " + json_config['folder_name'], file=code)
        print("naming_media = " + json_config['naming_media'], file=code)
        print("naming_file = " + json_config['naming_file'], file=code)
        print("", file=code)
        print("[update]", file=code)
        print("update_check = " + str(json_config['update_check']), file=code)
        print("", file=code)
        print("[log]", file=code)
        print("save_log = " + str(json_config['save_log']), file=code)
        print("", file=code)
        print("[media]", file=code)
        print("media_type = " + json_config['media_type'], file=code)
        print("sub_type = " + json_config['sub_type'], file=code)
        print("media_path = " + json_config['media_path'], file=code)
        print("", file=code)
        print("[escape]", file=code)
        print("literals = " + json_config['literals'], file=code)
        print("folders = " + json_config['folders'], file=code)
        print("string = " + json_config['string'], file=code)
        print("", file=code)
        print("[debug_mode]", file=code)
        print("switch = " + str(json_config['switch_debug']), file=code)
        print("", file=code)
        print("[emby]", file=code)
        print("emby_url = " + json_config['emby_url'], file=code)
        print("api_key = " + json_config['api_key'], file=code)
        print("", file=code)
        print("[mark]", file=code)
        print("poster_mark = " + str(json_config['poster_mark']), file=code)
        print("thumb_mark = " + str(json_config['thumb_mark']), file=code)
        print("mark_size = " + str(json_config['mark_size']), file=code)
        print("mark_type = " + json_config['mark_type'], file=code)
        print("mark_pos = " + json_config['mark_pos'], file=code)
        print("# mark_size : range 1-5", file=code)
        print("# mark_type : sub, leak, uncensored", file=code)
        print("# mark_pos  : bottom_right or bottom_left or top_right or top_left", file=code)
        print("", file=code)
        print("[uncensored]", file=code)
        print("uncensored_prefix = " + str(json_config['uncensored_prefix']), file=code)
        print("uncensored_poster = " + str(json_config['uncensored_poster']), file=code)
        print("# 0 : official, 1 : cut", file=code)
        print("", file=code)
        print("[file_download]", file=code)
        print("nfo = " + str(json_config['nfo_download']), file=code)
        print("poster = " + str(json_config['poster_download']), file=code)
        print("fanart = " + str(json_config['fanart_download']), file=code)
        print("thumb = " + str(json_config['thumb_download']), file=code)
        print("", file=code)
        print("[extrafanart]", file=code)
        print("extrafanart_download = " + str(json_config['extrafanart_download']), file=code)
        print("extrafanart_folder = " + str(json_config['extrafanart_folder']), file=code)

    code.close()


def check_pic(path_pic):
    try:
        img = Image.open(path_pic)
        img.load()
        return True
    except (FileNotFoundError, OSError):
        # print('damaged file')
        return False
