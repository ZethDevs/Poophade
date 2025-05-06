import re, json, requests, bs4
from bs4 import BeautifulSoup as bs
from concurrent.futures import ThreadPoolExecutor

class PoopDownload():

    #--> konstruktor
    def __init__(self) -> None:

        self.r    = requests.Session()
        self.url  = None
        self.host = None

        self.data_file : list = []
        self.result    : dict = {
            'status' : 'failed',
            'data'   : self.data_file,
        }

    #--> redirect karena domain berubah-ubah
    def redirect(self, url:str) -> None:

        try:
            response = self.r.get(url, allow_redirects=True)
            self.url = response.url
            self.host = 'https://{}/'.format(self.url.split('/')[2])
        except Exception:
            pass

    #--> landing, buat sortir tipe data yang dikirim dari client (str/list)
    def execute(self, raw_url:str|list) -> None:

        if type(raw_url) == list:
            with ThreadPoolExecutor(max_workers=10) as TPE:
                for i in raw_url:
                    TPE.submit(self.get_file, i)
        elif type(raw_url) == str:
            self.get_file(raw_url)

        if len(self.data_file):
            self.result['status'] = 'success'

    #--> main method
    def get_file(self, url:str):

        #--> cek apakah url valid
        self.redirect(url)
        if not self.host: return

        #--> cek tipe url
        url_type : str = self.url.split('/')[3].lower()

        if url_type == 'f': #--> folder
            id_folder = self.url.split('/')[4]
            self.get_data_multi_file(id_folder)

        elif url_type == 'd' or url_type == 'e': #--> file
            id_file = self.url.split('/')[4]
            self.get_data_single_file(id_file)

    #--> dapetin semua id_file dari folder
    def get_data_multi_file(self, id_folder:str) -> None:

        try:

            url : str = f'{self.host}f/{id_folder}'
            response : object = self.r.get(url, headers={'referer':self.host}, allow_redirects=False)
            response_bs4 : str = bs(response.content, 'html.parser')

            #--> fatal : regex url
            find_a = response_bs4.find_all('a', {'href':True, 'class':'title_video'})
            list_id_file = [re.search(r'href="(.*?)"',str(item)).group(1).split('/')[-1] for item in find_a]

            if len(list_id_file):
                with ThreadPoolExecutor(max_workers=10) as TPE:
                    for id_file in list_id_file:
                        TPE.submit(self.get_data_single_file, id_file)

        except Exception: pass

    #--> dapetin data tiap file
    def get_data_single_file(self, id_file:str) -> None:

        packed_data = {
            'id' : id_file,
            **self.get_file_information(id_file), #--> ambil informasi suatu file (ukuran, waktu, dll)
            **self.get_thumbnail_and_video_url(id_file), #--> ambil url gambar & video
        }

        if all(list(packed_data.values())):
            self.data_file.append(packed_data)

    #--> dapetin informasi dari file (ukuran, waktu, dll)
    def get_file_information(self, id_file:str) -> dict[str,str|int]:

        try:

            url : str = f'{self.host}d/{id_file}'
            response : object = self.r.get(url, headers={'referer':self.host}, allow_redirects=False)
            response_bs4 : str = bs(response.content, 'html.parser')

            #--> fatal : regex url
            find_div = response_bs4.find('div', {'class':'info'})
            file_name = find_div.find('h4').text.strip()
            file_size = find_div.find('div', {'class':'size'}).text.strip()
            file_duration = find_div.find('div', {'class':'length'}).text.strip()
            file_upload_date = find_div.find('div', {'class':'uploadate'}).text.strip()

        except Exception:
            file_name, file_size, file_duration, file_upload_date = None, None, None, None

        return({
            'filename'    : file_name,
            'size'        : file_size,
            'duration'    : file_duration,
            'upload_date' : file_upload_date,
        })

    #--> dapetin url gambar & video
    def get_thumbnail_and_video_url(self, id_file:str) -> dict[str,str]:

        try:

            url : str = f'https://poophd.video-src.com/vplayer?id={id_file}'
            response : object = self.r.get(url, headers={'referer':self.host}, allow_redirects=False)
            response_text : str = response.text.replace('\\','')

            #--> fatal : regex url
            raw_match : str = re.search(r'player\((.*?)\);',response_text).group(1)
            match : tuple =  eval(f'({raw_match})')
            thumbnail_url, video_url = match[1].replace(' ','%20'), match[-1].replace(' ','%20')
            try:
                match_old = re.search(r'https://(.*?)/',thumbnail_url).group(1)
                match_new = re.search(r'https://(.*?)/',video_url).group(1)
                thumbnail_url = thumbnail_url.replace(match_old, match_new)
            except Exception: pass

        except Exception:
            thumbnail_url, video_url = None, None

        return({
            'thumbnail_url' : thumbnail_url,
            'video_url'     : video_url,
        })

if __name__ == '__main__':

     poop = PoopDownload()
     
    #--> menerima lebih dari 1 video (folder)
#     url = 'https://dood.is/f/ovnoy09zqlt'
    # poop.execute(url)

     # menerima file 1 video
  #   url = 'https://vidoy.pro/d/qf5i0z2a0xav'
#     poop.execute(url)

 #    print(json.dumps(poop.result, indent=4))