# Bibliotecas utilizadas :  
from typing import Callable, Tuple
from PIL import Image
from main import *
import stats
import image

# Método utilizado para cifrar ou decrifrar uma imagem, dependendo de qual método você passa para o parâmetro 'crypt'
# Parâmetros : método de cifragem/decifragem, chave, número de rodadas, caminho da imagem original e caminho para a imagem de saída
def crypt_image(crypt, key, rounds, original_image_path, output_path):
    # Abre a imagem original e lê seu tamanho
    image = Image.open(original_image_path) 
    width, height = image.size 
    
    # Contém a sequência de bytes que representa a imagem em formato RGB
    rgb_bytes = b''.join([bytes(pixel) for pixel in image.getdata()])
    
    # Cifra os bytes RGB 
    encrypted_bytes = crypt(rgb_bytes, key, rounds)
    
    # Gera o Texto Cifrado, com o tamanho da imagem original e os bits RGB's cifrados 
    image = Image.frombytes('RGB', (width, height), encrypted_bytes)
    # Salva a imagem cifrada no caminho indicado por parâmetro
    image.save(output_path)

# Método do teste avalanche passando como paramêtro o método encrypt
def avalanche(encrypt):
    # Realiza 5 vezes a avalanche
    # Parâmetros : método cifragem/decifragem, profundidade (número de rodadas) , número de bits testados 
    for i in range(5):
        stats.avalanche(encrypt, i + 1, 24)
# Gera chave aleatória 
key = random_bytes(16)

def experiments(name, encrypt, decrypt):
    # Crifa a imagem com o método crypt_image, passando o método encrypt como parâmetro
    crypt_image(encrypt, key, 16, f'lenna.png', f'output/{name}_encrypted_lenna.png')

    # Decifra a imagem com o método decrypt_image, passando o método decrypt como parâmetro
    crypt_image(decrypt, key, 16, f'output/{name}_encrypted_lenna.png', f'output/{name}_decrypted_lenna.png')

    # Avalanche :
    avalanche(encrypt)

    # Correlação : 
    image.correlation(f'output/{name}_encrypted_lenna.png', f'output/{name}_correlation_encrypted_lenna.png')

    # Entropia : 
    entropy = stats.entropy(f'output/{name}_encrypted_lenna.png')
    print(f'entropy: {entropy}')
  
    # Histograma : 
    stats.histogram(f'output/{name}_encrypted_lenna.png', f'output/{name}_histogram_encrypted_lenna.png')




# Salva os resultados de correlação e histograma em caminhos diferentes :   
image.correlation(f'lenna.png', f'output/correlation_lenna.png')
stats.histogram(f'lenna.png', f'output/histogram_lenna.png')

# run experiments
experiments('3des', tripleDesEncrypt, tripleDesDecrypt)
