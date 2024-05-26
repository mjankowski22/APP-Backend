import requests


#Tu port może być do zmiany jak inaczej ustawicie serwer
url = 'http://localhost:5000/upload_file'  
file_path = 'data.csv'  

if __name__ == '__main__':
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)

    if response.status_code == 200:
        print('Plik został przesłany i zapisany')
    else:
        print('Wystąpił błąd:', response.text)