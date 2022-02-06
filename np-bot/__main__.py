from concurrent.futures import process
import logging
import datetime
import sys
# import os
from io import BytesIO

from typing import List
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from PIL import Image
    
from . import config as CFG

now = datetime.datetime.now()
# module_dir = os.path.dirname(__file__)

logging.basicConfig(
    handlers=[
        logging.FileHandler(f"logs/{now.year}-{now.month}-{now.day}.log"),
        logging.StreamHandler()
    ],
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

def save_pet_image (pet: WebElement, driver: webdriver.Chrome):
    
    name = pet.find_element(By.ID, f"{pet.get_property('id')}_name").text
    # filename = os.path.join(module_dir, f"pets/{name}.png")
    
    card_img = Image.open(BytesIO(driver.get_screenshot_as_png()))
    card_location = pet.location
    card_size = pet.size
    
    left = card_location['x']
    top = card_location['y']
    right = card_location['x'] + card_size['width']
    bottom = card_location['y'] + card_size['height']
    
    card_img = card_img.crop((left, top, right, bottom)) 
    card_img.save(f"pets/{name}.png")
                
    logging.info(f"Pet saved.")
    
    return

def login (driver: webdriver.Chrome, config):
    
    try:
        logging.info(f"Attempting to log in as '{config['login']['username']}'...")
    
        driver.get('https://www.neopets.com/login/')
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="login"]')))
        
        driver.find_element(By.ID, 'loginUsername').send_keys(config['login']['username'])
        driver.find_element(By.ID, 'loginPassword').send_keys(config['login']['password'])
        
        driver.find_element(By.ID, 'loginButton').click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[20]/div[2]/div[2]')))
        
    except TimeoutException:
        # driver.get_screenshot_as_file(os.path.join(module_dir, 'screenshots/login_failed.png'))
        driver.get_screenshot_as_file('screenshots/login_failed.png')
        logging.error(f"Login failed. Screenshot saved as 'login_failed.png'.")
        
        sys.exit()
    
    logging.info(f"Login success.")
    return

def goto_pound (driver: webdriver.Chrome):
    
    try:
        logging.info("Loading 'adopt' section of the pound...")
        
        driver.get('https://www.neopets.com/pound/adopt.phtml')
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[4]/div[3]/table/tbody/tr/td/div[2]/div[3]/div/a')))
        
    except TimeoutException:
        # driver.get_screenshot_as_file(os.path.join(module_dir, 'screenshots/nav_failed_(pound).png'))
        driver.get_screenshot_as_file('screenshots/nav_failed_(pound).png')
        logging.error("Failed to navigate to the pound. Screenshot saved as 'nav_failed_(pound).png'")
    
        sys.exit()
    
    logging.info("Navigation successful.")
    return
    
def filter_pets (driver: webdriver.Chrome, color_blacklist: list) -> List[WebElement] | None:
    
        rare_pets = []
        
        try:
            logging.info("Attempting to grab pet data...")
        
            pet0_color = driver.find_element(By.ID, f"pet0_color").text.lower()
            pet1_color = driver.find_element(By.ID, f"pet1_color").text.lower()
            pet2_color = driver.find_element(By.ID, f"pet2_color").text.lower()
        
            if (pet0_color not in color_blacklist):
                rare_pets.append(driver.find_element(By.ID, 'pet0'))
                
            if (pet1_color not in color_blacklist):
                rare_pets.append(driver.find_element(By.ID, 'pet1'))
                
            if (pet2_color not in color_blacklist):
                rare_pets.append(driver.find_element(By.ID, 'pet2'))
            
        except NoSuchElementException:
            logging.error("Failed to grab pet data! Web page likely didn't load properly.")
            return None
        
        logging.info(f"Pet data retrieved [{pet0_color},{pet1_color},{pet2_color}]. Checking for rare colors...")
                
        return (rare_pets if len(rare_pets) > 0 else None)

def main():
    
    config = CFG.load_config()
    
    options = webdriver.ChromeOptions()
    options.headless = True
    options.add_argument('load-extension=' + 'np-bot/ublock')
    
    driver = webdriver.Chrome(options=options)
    # driver.create_options()
    driver.set_window_size(width=1920, height=1080)
    
    login (driver, config)
    
    attempt = 1
    max_attempts = config['max_attempts']
    
    while True:
    
        logging.info(f"Running analysis batch {attempt} of {(max_attempts if max_attempts > 0 else '∞')}...")
            
        goto_pound(driver)

        # Go over pound data
        rare_pets = filter_pets (driver, config['color_blacklist'])
        
        if rare_pets:
            logging.info(f'Saving {len(rare_pets)} pet card(s)...')
            
            for pet in rare_pets:
                save_pet_image (pet, driver)
                
            logging.info("All cards saved to 'pets' directory.")
            
        else:
            logging.info('Failed to find any rare colors. Retrying with next adoption page...')
            
        if (max_attempts != 0 and attempt == max_attempts):
            logging.info('Max attempts reached. Gracefully killing program.')
            break
            
        attempt += 1

    driver.find_element(By.ID, 'logout_link').click()
    WebDriverWait(driver, 1)
    driver.close()

if __name__ == '__main__':
    
    try:
        main()
        
    except KeyboardInterrupt:
        logging.warning('Keyboard interrupt detected. Gracefully killing program.')