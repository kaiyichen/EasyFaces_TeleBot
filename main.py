import os
import facedetector
import requests
import urllib.request
import telebot

from telebot.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

# TelegramBot
API_KEY = os.getenv('API_KEY') 
bot = telebot.TeleBot(API_KEY)


command = [BotCommand("start","Starts the bot"),]

bot.set_my_commands(command)

global pictures, title, selection, packname, set_name
pictures = {}
title = {}
selection = {}
packname = {}
set_name = {}

def request_start(chat_id):
  """
  Helper function to request user to execute command /start
  """
  bot.send_message(chat_id=chat_id, text='Please start the bot by sending /start')
  
  return


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
  """
  Handles the execution of the respective functions upon receipt of the callback query
  """
  
  chat_id = call.message.chat.id
  data = call.data
  

  intent, data = data.split()[0], data.split()[1:]
  
  if intent == 'convert':
    convert_sticker(chat_id, data)
  elif intent == 'create':
    create_pack(chat_id, data)
  elif intent == 'add':
    add_to_pack(chat_id, data)
  else:
    print(f'{intent}: Callback not implemented')

@bot.message_handler(commands=['start'])
def start(message):
  """
  Command that welcomes the user and configures the required initial setup
  """

  if message.chat.type == 'private':
    chat_user = message.chat.first_name
  else:
    chat_user = message.chat.title
  
  message_text = f'Hi {chat_user}! Send me a .jpg of faces and I will extract them out to stickers for you!'
  
  bot.reply_to(message, message_text)



@bot.message_handler(content_types=['photo'])
def submit(message):
  """
  Command that takes in the user's photo and extracts out faces
  """
  try:
    filename, headers = get_photo(message)
  except IndexError as e:
    print(str(e) + ': No faces detected')
    bot.send_message(message.chat.id, text='No faces detected! Try again with a different photo.')
    return

  faces = facedetector.convert(filename)

  if not len(faces):
    print('No faces detected')
    bot.send_message(message.chat.id, text='No faces detected! Try again with a different photo.')
    return
  
  bot.send_message(message.chat.id, "Faces detected:")
  counter = 1
  
  if message.chat.id not in pictures:
    pictures[message.chat.id] = dict()
  buttons = []
  row = []
  for face in faces: 
    bot.send_photo(message.chat.id, face, caption=str(counter))
    pictures[message.chat.id][counter] = face
    button = InlineKeyboardButton(
      text=str(counter),
      callback_data='convert sticker ' + str(counter)
    )
    if not (counter - 1) % 3:
      # new row
      buttons.append(row)
      row = []
    row.append(button)  
    counter += 1

  buttons.append(row)
    
  chat_text = 'Please select the photo you would like to turn into a sticker'
    
  bot.send_message(
    chat_id=message.chat.id,
    text=chat_text,
    reply_markup=InlineKeyboardMarkup(buttons)
  )
  
  
def convert_sticker(chat_id, data):
  subintent, number = data
  selection[chat_id] = int(number)
  chat_text = 'Would you like to create a new sticker pack or add to an existing pack that you made through EasyFaces?'
  buttons = []
  create_button = InlineKeyboardButton(
    text='Create new pack',
    callback_data= 'create pack ' + number
    
  )
  add_button = InlineKeyboardButton(
    text='Add to existing pack',
    callback_data= 'add sticker ' + number
  )
  
  buttons = [[create_button], [add_button]]
  bot.send_message(
    chat_id=chat_id,
    text=chat_text,
    reply_markup=InlineKeyboardMarkup(buttons)
  )  

def create_pack(chat_id, data):
 
  chat_text = 'What would you like your title to be? It must begin with a letter and contain only english letters, digits and underscores, with no consecutive underscores.'
  sent = bot.send_message(chat_id=chat_id, text=chat_text)
  bot.register_next_step_handler(sent, create_title)

def check_pack_name(packname):
  if not packname[0].isalpha():
    return False
  elif '__' in packname:
    return False
  elif not packname.replace('_', '').isalnum():
    return False
  else:
    return True

def create_title(message):
  id = message.chat.id
  title[id] = message.text
  error_1 = "A request to the Telegram API was unsuccessful. Error code: 400. Description: Bad Request: STICKERSET_INVALID"
  error_2 = "A request to the Telegram API was unsuccessful. Error code: 400. Description: Bad Request: sticker set name is already occupied"
  packnum = 0

  if message.text is None:
    bot.send_message(chat_id=id, text='Wrong format. Please send a text.')
    return

  packname[id] =  message.text + str(id) + "_by_EasyFacesBot"
  if not check_pack_name(packname[id]):
    bot.send_message(chat_id=id, text='Invalid sticker set name. Please start again.')
    return
  packname_found = 0
  max_stickers = 120
  while not packname_found:
    try:
      stickerset = bot.get_sticker_set(packname[id])
      if len(stickerset.stickers) >= max_stickers:
        packnum += 1
        packname[id] = title + str(packnum) + "_" + str(id) + "_by_EasyFacesBot"
      else:
        packname_found = 1
        bot.send_message(chat_id=id, text=f'Sticker set name is already occupied. Your pack can be found here: t.me/addstickers/{packname[id]}')
        return
    except Exception as e:
      print(str(e))
      if str(e) == error_1:
        packname_found = 1
      elif str(e) == error_2:
        bot.send_message(chat_id=id, text=f'Sticker set name is already occupied. Your pack can be found here: t.me/addstickers/{packname[id]}')
        return
  print(packname[id])
  chat_text = 'Please send an emoji to associate with your sticker.'
  sent = bot.send_message(id, text=chat_text)
  bot.register_next_step_handler(sent, create_pack_final)

def create_pack_final(message):
  id = message.chat.id
  bot.create_new_sticker_set(id, packname[id], title[id], message, pictures[id][selection[id]], None)
  stickers = bot.get_sticker_set(packname[id]).stickers
  new_sticker = stickers[0]
  bot.send_sticker(id, new_sticker.file_id)
  chat_text = 'You successfully created a new sticker pack!'
  bot.send_message(id, text=chat_text)



def add_to_pack(chat_id, data):
  chat_text = 'Please send an existing sticker from the sticker pack you would like to add to.'
  sent = bot.send_message(chat_id, text=chat_text)
  bot.register_next_step_handler(sent, get_set_name)
  

def get_set_name(message):
  """
  Command that takes in the user's sticker and retrieves the sticker set name
  """
  id = message.chat.id
  try:
    set_name[id] = message.sticker.set_name
  except Exception as e:
    print(str(e) + 'Not a sticker.')
    bot.send_message(id, text='You did not send a sticker. Please restart the process.')
    return
  print(f"str(id): {str(id)}, set_name[id]: {set_name[id]}")
  length = len(set_name[id])  
  if str(id) not in set_name[id] or set_name[id][length - 17:] != '_by_EasyFacesBot':
    print('This sticker pack does not belong to you.')
    bot.send_message(id, text='This sticker pack does not belong to you.')
    return
  chat_text = 'Please send an emoji to associate with your sticker.'
  sent = bot.send_message(id, text=chat_text)
  bot.register_next_step_handler(sent, add_to_pack_final)


def add_to_pack_final(message):
  # if emoji
  id = message.chat.id
  try:
    if bot.add_sticker_to_set(user_id=id, name=set_name[id], png_sticker=pictures[id][selection[id]], emojis=message.text):
      stickers = bot.get_sticker_set(set_name[id]).stickers
      new_sticker = stickers[len(stickers) - 1]
      bot.send_sticker(id, new_sticker.file_id)
    else:
      bot.send_message(id, text="Adding failed. Please ensure you send an emoji and start again.")
  except Exception as e:
    print(str(e) + f' set_name: {set_name[id]}, user_id: {id}, emojis: {message.text}')
    bot.send_message(id, text="Adding failed. Please ensure you send an emoji and start again.")

  
def get_photo(message):
  file_id = message.photo[3].file_id
  file_path_url = f'https://api.telegram.org/bot{API_KEY}/getFile?file_id={file_id}'
  file_path_response = requests.get(file_path_url)
  dict = file_path_response.json()
  photo_path = dict["result"]["file_path"]
  photo_path_url = f'https://api.telegram.org/file/bot{API_KEY}/{photo_path}'
  return urllib.request.urlretrieve(photo_path_url)


def photo_chosen(chat_id,message):

  bot.send_message(chat_id=chat_id, text='Please select the photo you would like to turn into a sticker')
  #Retrieve test
  message_text = message.text
  return message_text

bot.infinity_polling()
