# -*- coding: utf-8 -*-
# import discord
import asyncio
import requests
import platform
import os
import glob
import httpx
from src.trackers.COMMON import COMMON
from src.console import console


class LCD():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """
    def __init__(self, config):
        self.config = config
        self.tracker = 'LCD'
        self.source_flag = 'LOCADORA'
        self.search_url = 'https://locadora.cc/api/torrents/filter'
        self.torrent_url = 'https://locadora.cc/torrents/'
        self.upload_url = 'https://locadora.cc/api/torrents/upload'
        self.signature = "\n[center][url=https://github.com/Audionut/Upload-Assistant]Created by Audionut's Upload Assistant[/url][/center]"
        self.banned_groups = [""]
        pass

    async def upload(self, meta, disctype):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await common.unit3d_edit_desc(meta, self.tracker, self.signature)
        cat_id = await self.get_cat_id(meta['category'], meta.get('edition', ''), meta)
        type_id = await self.get_type_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'])
        region_id = await common.unit3d_region_ids(meta.get('region'))
        distributor_id = await common.unit3d_distributor_ids(meta.get('distributor'))
        name = await self.edit_name(meta)
        if meta['anon'] == 0 and not self.config['TRACKERS'][self.tracker].get('anon', False):
            anon = 0
        else:
            anon = 1

        if meta['bdinfo'] is not None:
            mi_dump = None
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
            bd_dump = None
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[LCD]DESCRIPTION.txt", 'r', encoding='utf-8').read()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[LCD].torrent", 'rb')
        files = {'torrent': ("placeholder.torrent", open_torrent, "application/x-bittorrent")}
        base_dir = meta['base_dir']
        uuid = meta['uuid']
        specified_dir_path = os.path.join(base_dir, "tmp", uuid, "*.nfo")
        nfo_files = glob.glob(specified_dir_path)
        nfo_file = None
        if nfo_files:
            nfo_file = open(nfo_files[0], 'rb')
        if nfo_file:
            files['nfo'] = ("nfo_file.nfo", nfo_file, "text/plain")
        data = {
            'name': name,
            'description': desc,
            'mediainfo': mi_dump,
            'bdinfo': bd_dump,
            'category_id': cat_id,
            'type_id': type_id,
            'resolution_id': resolution_id,
            'tmdb': meta['tmdb'],
            'imdb': meta['imdb'],
            'tvdb': meta['tvdb_id'],
            'mal': meta['mal_id'],
            'igdb': 0,
            'anonymous': anon,
            'stream': meta['stream'],
            'sd': meta['sd'],
            'keywords': meta['keywords'],
            'personal_release': int(meta.get('personalrelease', False)),
            'internal': 0,
            'featured': 0,
            'free': 0,
            'doubleup': 0,
            'sticky': 0,
        }
        # Internal
        if self.config['TRACKERS'][self.tracker].get('internal', False) is True:
            if meta['tag'] != "" and (meta['tag'][1:] in self.config['TRACKERS'][self.tracker].get('internal_groups', [])):
                data['internal'] = 1

        if region_id != 0:
            data['region_id'] = region_id
        if distributor_id != 0:
            data['distributor_id'] = distributor_id
        if meta.get('category') == "TV":
            data['season_number'] = meta.get('season_int', '0')
            data['episode_number'] = meta.get('episode_int', '0')
        headers = {
            'User-Agent': f'Upload Assistant/2.2 ({platform.system()} {platform.release()})'
        }
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip()
        }

        if meta['debug'] is False:
            response = requests.post(url=self.upload_url, files=files, data=data, headers=headers, params=params)
            try:
                meta['tracker_status'][self.tracker]['status_message'] = response.json()
                # adding torrent link to comment of torrent file
                t_id = response.json()['data'].split(".")[1].split("/")[3]
                meta['tracker_status'][self.tracker]['torrent_id'] = t_id
                await common.add_tracker_torrent(meta, self.tracker, self.source_flag, self.config['TRACKERS'][self.tracker].get('announce_url'), "https://locadora.cc/torrents/" + t_id)
            except Exception:
                console.print("It may have uploaded, go check")
                return
        else:
            console.print("[cyan]Request Data:")
            console.print(data)
            meta['tracker_status'][self.tracker]['status_message'] = "Debug mode enabled, not uploading."
        open_torrent.close()

    async def get_cat_id(self, category_name, edition, meta):
        category_id = {
            'MOVIE': '1',
            'TV': '2',
            'ANIMES': '6'
        }.get(category_name, '0')
        if meta['anime'] is True and category_id == '2':
            category_id = '6'
        return category_id

    async def get_type_id(self, type):
        type_id = {
            'DISC': '1',
            'REMUX': '2',
            'ENCODE': '3',
            'WEBDL': '4',
            'WEBRIP': '5',
            'HDTV': '6'
        }.get(type, '0')
        return type_id

    async def get_res_id(self, resolution):
        resolution_id = {
            # '8640p':'10',
            '4320p': '1',
            '2160p': '2',
            # '1440p' : '2',
            '1080p': '3',
            '1080i': '34',
            '720p': '5',
            '576p': '6',
            '576i': '7',
            '480p': '8',
            '480i': '9',
            'Other': '10',
        }.get(resolution, '10')
        return resolution_id

    async def search_existing(self, meta, disctype):
        dupes = []
        console.print("[yellow]Buscando por duplicatas no tracker...")
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'tmdbId': meta['tmdb'],
            'categories[]': await self.get_cat_id(meta['category'], meta.get('edition', ''), meta),
            'types[]': await self.get_type_id(meta['type']),
            'resolutions[]': await self.get_res_id(meta['resolution']),
            'name': ""
        }
        if meta['category'] == 'TV':
            params['name'] = params['name'] + f" {meta.get('season', '')}"
        if meta.get('edition', "") != "":
            params['name'] = params['name'] + f" {meta['edition']}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url=self.search_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for each in data['data']:
                        result = [each][0]['attributes']['name']
                        dupes.append(result)
                else:
                    console.print(f"[bold red]Failed to search torrents. HTTP Status: {response.status_code}")
        except httpx.TimeoutException:
            console.print("[bold red]Request timed out after 5 seconds")
        except httpx.RequestError as e:
            console.print(f"[bold red]Unable to search for existing torrents: {e}")
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {e}")
            await asyncio.sleep(5)

        return dupes

    async def edit_name(self, meta):

        name = meta['uuid'].replace('.mkv', '').replace('.mp4', '').replace(".", " ").replace("DDP2 0", "DDP2.0").replace("DDP5 1", "DDP5.1").replace("H 264", "H.264").replace("H 265", "H.265").replace("DD+7 1", "DDP7.1").replace("AAC2 0", "AAC2.0").replace('DD5 1', 'DD5.1').replace('DD2 0', 'DD2.0').replace('TrueHD 7 1', 'TrueHD 7.1').replace('DTS-HD MA 7 1', 'DTS-HD MA 7.1').replace('DTS-HD MA 5 1', 'DTS-HD MA 5.1').replace("TrueHD 5 1", "TrueHD 5.1").replace("DTS-X 7 1", "DTS-X 7.1").replace("DTS-X 5 1", "DTS-X 5.1").replace("FLAC 2 0", "FLAC 2.0").replace("FLAC 5 1", "FLAC 5.1").replace("DD1 0", "DD1.0").replace("DTS ES 5 1", "DTS ES 5.1").replace("DTS5 1", "DTS 5.1").replace("AAC1 0", "AAC1.0").replace("DD+5 1", "DDP5.1").replace("DD+2 0", "DDP2.0").replace("DD+1 0", "DDP1.0")

        return name
