from bs4 import BeautifulSoup
import requests
import hsk1, hsk2, hsk3, hsk4, hsk5, hsk6

def downloadCharImages(words):
    charDownloadCount = 0
    sheetDownloadCount = 0
    for word in words:
        whole_word = word['hanzi']

        urls = []
        characters =[]

        for single in whole_word:
            if(single not in characters):
                characters.append(single)

                url = f"https://www.strokeorder.com/chinese/{single}"
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')


                div = soup.find_all('div', class_='stroke-article-content')
                div_sheet = div[1]
                div_char = div[0]
                if div_char is not None:
                    img = div_char.find('img')
                    if img is not None:
                        img_url = f"https://www.strokeorder.com{img['src']}"
                        response = requests.get(img_url)
                        if response.status_code == 200:
                            with open(f"./hsk4/{single}.png", "wb") as f:
                                f.write(response.content)
                            charDownloadCount += 1
                            print("charDownloaded: " + str(charDownloadCount))
                        else:
                            print(f"Failed to download image for character: {single}")
                # for character sheet
                if div_sheet is not None:
                    img = div_sheet.find('img')
                    if img is not None:
                        img_url = f"https://www.strokeorder.com{img['src']}"
                        response = requests.get(img_url)
                        if response.status_code == 200:
                            with open(f"./hsk4/sheets/{single}-sheet.png", "wb") as f:
                                f.write(response.content)
                            urls.append(img_url)
                            sheetDownloadCount += 1
                            print("sheetDownloaded: " + str(sheetDownloadCount))
                        else:
                            print(f"Failed to download image for character: {single}")
        # return render_template('writing_practice.html',
        #                     title='Practice' , 
        #                     img_urls=urls, character=character)


downloadCharImages(hsk4.words)