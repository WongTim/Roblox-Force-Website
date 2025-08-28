from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
from io import BytesIO
from werkzeug.utils import secure_filename

import json
import os, secrets
import random


app = Flask(__name__)

# Get from environment
secret = os.getenv("SECRET_KEY")


if not secret:
    if os.getenv("FLASK_ENV") == "production":
        raise RuntimeError("SECRET_KEY not set in environment. Please create a .env file with SECRET_KEY=<your key>")
    # For local dev only: auto-generate a random one
    secret = secrets.token_hex(32)

app.config["SECRET_KEY"] = secret


#===========================
#   1. GLOBAL VARIABLES
#===========================
class Flags():
    def __init__(self):
        self.data = {
        "timwong_alt2" : False,
        "timwong_alt3" : False,
        "ellis_alt2": False,
        "ellis_alt3": False,
        "bala_alt2": False,
        "bala_alt3": False,
        "using_alt2": False,
        "using_alt3": False,
        "unlocked": False,
        "t_badge": False,
        "e_badge": False,
        "b_badge": False,
        "u_badge": False,
        "quiz_badge": False,
        "uploader": False,
        "t_set": 0,
        "e_set": 0,
        "b_set": 0,
        "u_set": 0
        }

    def get_data(self):
        return self.data
    
    def update_data(self, new_data):
        self.data = new_data
    
    def get_profile(self):
        self.tim = get_cartoon_costume('timwong',self.data['t_set'])[0]
        self.ellis = get_cartoon_costume('ellisl4d2character',self.data['e_set'])[0]
        self.bala = get_cartoon_costume('bala3imcu',self.data['b_set'])[0]
        self.using = get_cartoon_costume('using456',self.data['u_set'])[0]
        return [self.tim,self.ellis,self.bala,self.using]


    def import_data(self):
        pass
    

    def save_data(self):
        with open("saves.json", "r+") as file:
            all_saves = json.load(file)
            all_saves[str(self.name)] = self.data   # Update only this slot
            file.seek(0)
            json.dump(all_saves, file, indent=4)    # Write the whole structure back
            file.truncate()
            self.status = True
            return True
        return False
    

    def get_progress(self):

        if self.data is not None:
            costume_count = 0   # How many of these flags are costumes?
            unlocked_costumes = 0  # How many costumes are unlocked?

            award = None
            for key, value in self.data.items():
                if "_alt" in key:   # If the value is a costume variable
                    costume_count += 1  
                    if value == True:
                        unlocked_costumes += 1
            progress = (unlocked_costumes/costume_count)*100   # Percentage of total costumes unlocked 
            if self.data['unlocked'] == True:
                progress += 1

            if 100 <= progress < 101:
                award = "metallic-gold"
            elif progress == 101:
                award = "rainbow"

            if str(progress)[-2:] == ".0":
                progress = str(progress)[:-2]
                return (progress,award)
            else:
                return (str(round(progress,1)),award)   # e.g (100,"metallic-gold")
        return [None,None]


    def import_from_json(self, filename):
        with open(filename,"r") as file:
            self.data = json.load(file)
            return True
        return False
    
    def export_to_file(self):
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4, ensure_ascii=False)
        return filename


    def print_save(self):
        '''
        Displays the contents inside the object
        '''
        progress,award = self.get_progress()
        if self.data is not None:
            print(f"{'Name':<20}{self.name}")
            print(25*"-")
            for key, value in self.data.items():
                print(f"{key:<20}{value}")
            print(f"{'Progress (%)':<20}{progress}")
            print(f"{'Award':<20}{award}")

            print(f"{'timwong':<20}{self.tim}")
            print(f"{'ellis':<20}{self.ellis}")
            print(f"{'bala':<20}{self.bala}")
            print(f"{'using':<20}{self.using}")
        else:
            print(None)
        return
                

    
flags = Flags()


empty_flags = flags

# A comprehensive dictionary that maps the character's set costume to their colour. Used for member's page
costume_map = {
    'timwong': {
        0: ('_', 'gold'),
        1: ('_alt1_', 'white'),
        2: ('_alt2_', 'red'),
        3: ('_alt3_', 'green')
    },
    'ellis': {
        0: ('_', 'blue'),
        1: ('_alt1_', 'green'),
        2: ('_alt2_', 'pink'),
        3: ('_alt3_', 'gold')
    },
    'bala': {
        0: ('_', 'white'),
        1: ('_alt1_', 'green'),
        2: ('_alt2_', 'neon'),
        3: ('_alt3_', 'purple')
    },
    'using': {
        0: ('_', 'neon'),
        1: ('_alt1_', 'green'),
        2: ('_alt2_', 'purple'),
        3: ('_alt3_', 'pink')
    }
}

# Images make use of shortened versions of the character's names
truncate_names = {
    'timwong':'timwong',
    'ellisl4d2character':'ellis',
    'bala3imcu':'bala',
    'using456':'using'
}

# Alternative mapping for name truncations
reverse_truncate = {
    'timwong':'timwong',
    'ellis':'ellisl4d2character',
    'bala':'bala3imcu',
    'using':'using456'
}




#==========================
#   2. HELPER FUNCTIONS
#==========================


def get_directory(character):
    '''
    Gets the character's static directory where their images are stored
    '''
    dir = f'/static/members/{character}'
    return dir



def get_cartoon_costume(character, set_value):
    ''' 
    Returns -> tuple(image, colour)
    This is used for the 4 square icons in the Members page
    Meaning the cartoon versions

    '''
    char = truncate_names[character]   # A shortened version of the character's name
    suffix, color = costume_map.get(char, {}).get(set_value, ('', ''))
    cartoon_image = f"/static/members/{character}/{char}{suffix}cartoon.jpg"
    return cartoon_image, color




def get_character_alt(character,costume_number):
    ''' 
    Returns the image directory name for a character's costume.
    Adds in locked when costume is False.
    This is for an individual character's alternate costume pages.
    '''
    global flags
    folder = get_directory(character)   # Get the character's specific directory
    costume = ''    # e.g timwong_alt1
    status = False  # defaulted to locked
    if not 1 <= costume_number <= 3:
        return "costume_number can be only from 1-3"

    character = truncate_names[character]


    # Find the specified character in the flags dictionary
    for key,value in flags.get_data().items():
        if str(costume_number) in key and character in key:     # Match the character and its outfit with the flags
            costume = key   # costume takes on the name of the key
            status = value  # Update the status
            break

    # After matching, find out whether it's locked or not
    if status == False:
        status = "_locked"  # Put a 'locked' behind the costume name
    else:
        status = ""
    outfit = f'{folder}/{costume}{status}.jpg?'     # Sum up the name
    return outfit
    


def read_txt(filename):
    data = []
    with open(filename) as file:
        for line in file.readlines():
            data.append(line.strip())
    return data




#=========================
#   4. NAVIGATION BAR
#=========================


@app.route('/', methods=["GET", "POST"])
def home():
    global flags
    progress = flags.get_progress()[0]
    if request.method == "GET":
        return render_template("homepage.html",progress=float(progress))
    elif request.method == "POST":      # When user is submitting a feedback
        feedback = request.form.get("feedback")
        with open("Suggestions.txt", "a") as f:
            if feedback != ('' or None):
                f.write(feedback)
                f.write('\n')
        f.close()
        return render_template("homepage.html")





@app.route('/members', methods=["GET"])
def members():
    global flags
    tim = get_cartoon_costume("timwong",flags.get_data()['t_set'])
    ellis = get_cartoon_costume("ellisl4d2character",flags.get_data()['e_set'])
    bala = get_cartoon_costume("bala3imcu",flags.get_data()["b_set"])
    using = get_cartoon_costume("using456",flags.get_data()["u_set"])

    progress = flags.get_progress()[0]

    return render_template("members.html",tim=tim[0],ellis=ellis[0],\
                            bala=bala[0],using=using[0],colour1=tim[1],colour2=ellis[1],\
                            colour3=bala[1],colour4=using[1],unlocked=flags.get_data()['unlocked'],\
                            progress=float(progress))



@app.route('/games', methods=["GET"])
def games():
    return render_template('games.html')


#Memes page
@app.route('/memes', methods=["GET"])
def memes():
    return render_template('memes.html')

#Tutorials page
@app.route('/tutorials', methods=["GET"])
def tutorials():
    return render_template('tutorials.html')




#==================
#   5. TIMWONG
#==================

@app.route('/timwong', methods=["GET"])
def timwong():
    global flags
    old_guest = flags.get_data()['timwong_alt2']
    large_minion = flags.get_data()['timwong_alt3']
    if flags.get_data()["timwong_alt2"] == True and flags.get_data()["timwong_alt3"] == True:
        flags.get_data()["t_badge"] = True
    return render_template('timwong.html',timwong_alt2=old_guest,timwong_alt3=large_minion)




@app.route('/timwong_alt1', methods=["GET", "POST"])
def tim1():
    global flags
    t_set = flags.get_data()['t_set']

    if request.method == "GET":
        return render_template('timwong_alt1.html', t_set=t_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['t_set'] = 1
            t_set = flags.get_data()['t_set']
            flash("Vintage Flame portrait equipped! Return to the Members Page and check out timwong's new appearance!")
        elif action == "unequip":
            flags.get_data()['t_set'] = 0
            t_set = flags.get_data()['t_set']
            flash("Unequipped Vintage Flame portrait!")

        # Add a return for both cases
        return render_template('timwong_alt1.html', t_set=t_set)





@app.route('/timwong_alt2', methods=["GET", "POST"])
def tim2():
    global flags
    t_set = flags.get_data()['t_set']

    if request.method == "GET":
        return render_template('timwong_alt2.html', t_set=t_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['t_set'] = 2
            t_set = flags.get_data()['t_set']
            flash("Old Guest portrait equipped! Return to the Members Page and check out timwong's new appearance!")
        elif action == "unequip":
            flags.get_data()['t_set'] = 0
            t_set = flags.get_data()['t_set']
            flash("Unequipped Old Guest portrait!")

        # Add a return for both cases
        return render_template('timwong_alt2.html', t_set=t_set)






@app.route('/timwong_alt3', methods=["GET", "POST"])
def tim3():
    global flags
    t_set = flags.get_data()['t_set']

    if request.method == "GET":
        return render_template('timwong_alt3.html', t_set=t_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['t_set'] = 3
            t_set = flags.get_data()['t_set']
            flash("Large Minion portrait equipped! Return to the Members Page and check out timwong's new appearance!")
        elif action == "unequip":
            flags.get_data()['t_set'] = 0
            t_set = flags.get_data()['t_set']
            flash("Unequipped Large Minion portrait!")

        # Add a return for both cases
        return render_template('timwong_alt3.html', t_set=t_set)



@app.route('/unlock_tim',methods=["POST"])
def unlock_tim():
    '''
    Receives input code in order to unlock the alt2 and 3 outfits
    '''
    code = str(request.form.get('costume_unlock')).upper()
    if code == "T2":
        flags.get_data()['timwong_alt2'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/timwong/timwong_alt2.jpg',
            'caption': 'Old Guest unlocked!'
        })

    if code == "T3":
        flags.get_data()['timwong_alt3'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/timwong/timwong_alt3.jpg',
            'caption': 'Large Minion unlocked!'
        })
    else:
        return jsonify({'status': 'fail', 'message': 'Wrong code, try again!'}), 403




#=============================
#   6. ELLISL4D2CHARACTER
#=============================


@app.route('/ellisl4d2character', methods=["GET"])
def ellis():
    global flags
    candy_man = flags.get_data()['ellis_alt2']
    gold_viking = flags.get_data()['ellis_alt3']
    if flags.get_data()["ellis_alt2"] == True and flags.get_data()["ellis_alt3"] == True:
        flags.get_data()["e_badge"] = True
    return render_template('ellis.html',ellis_alt2=candy_man,ellis_alt3=gold_viking)





@app.route('/ellis_alt1', methods=["GET", "POST"])
def ellis1():
    global flags
    e_set = flags.get_data()['e_set']

    if request.method == "GET":
        return render_template('ellis_alt1.html', e_set=e_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['e_set'] = 1
            e_set = flags.get_data()['e_set']
            flash("Casual Blue portrait equipped! Return to the Members Page and check out ellis' new appearance!")
        elif action == "unequip":
            flags.get_data()['e_set'] = 0
            e_set = flags.get_data()['e_set']
            flash("Unequipped Casual Blue portrait!")

        # Add a return for both cases
        return render_template('ellis_alt1.html', e_set=e_set)




@app.route('/ellis_alt2', methods=["GET", "POST"])
def ellis2():
    global flags
    e_set = flags.get_data()['e_set']

    if request.method == "GET":
        return render_template('ellis_alt2.html', e_set=e_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['e_set'] = 2
            e_set = flags.get_data()['e_set']
            flash("Candy Man portrait equipped! Return to the Members Page and check out ellis' new appearance!")
        elif action == "unequip":
            flags.get_data()['e_set'] = 0
            e_set = flags.get_data()['e_set']
            flash("Unequipped Candy Man portrait!")

        # Add a return for both cases
        return render_template('ellis_alt2.html', e_set=e_set)





@app.route('/ellis_alt3', methods=["GET", "POST"])
def ellis3():
    global flags
    e_set = flags.get_data()['e_set']

    if request.method == "GET":
        return render_template('ellis_alt3.html', e_set=e_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['e_set'] = 3
            e_set = flags.get_data()['e_set']
            flash("Gilded Vault portrait equipped! Return to the Members Page and check out ellis' new appearance!")
        elif action == "unequip":
            flags.get_data()['e_set'] = 0
            e_set = flags.get_data()['e_set']
            flash("Unequipped Gilded Vault portrait!")

        # Add a return for both cases
        return render_template('ellis_alt3.html', e_set=e_set)




@app.route('/unlock_ellis',methods=["POST"])
def unlock_ellis():
    '''
    Receives input code in order to unlock the alt2 and 3 outfits
    '''
    code = str(request.form.get('costume_unlock')).upper()
    if code == "E2":
        flags.get_data()['ellis_alt2'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/ellisl4d2character/ellis_alt2.jpg',
            'caption': 'Candy Man unlocked!'
        })

    if code == "E3":
        flags.get_data()['ellis_alt3'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/ellisl4d2character/ellis_alt3.jpg',
            'caption': 'Gilded Vault unlocked!'
        })
    else:
        return jsonify({'status': 'fail', 'message': 'Wrong code, try again!'}), 403

    return "Locked. Use the popup to enter passcode."


#====================
#   7. BALA3IMCU
#====================

@app.route('/bala3imcu', methods=["GET"])
def bala():
    global flags
    riptide_aqua = flags.get_data()['bala_alt2']
    royal_madness = flags.get_data()['bala_alt3']
    if flags.get_data()["bala_alt2"] == True and flags.get_data()["bala_alt3"] == True:
        flags.get_data()["b_badge"] = True
    return render_template('bala.html',bala_alt2=riptide_aqua,bala_alt3=royal_madness)






@app.route('/bala_alt1', methods=["GET", "POST"])
def bala1():
    global flags
    b_set = flags.get_data()['b_set']

    if request.method == "GET":
        return render_template('bala_alt1.html', b_set=b_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['b_set'] = 1
            b_set = flags.get_data()['b_set']
            flash("Bombastic Sweater portrait equipped! Return to the Members Page and check out bala's new appearance!")
        elif action == "unequip":
            flags.get_data()['b_set'] = 0
            b_set = flags.get_data()['b_set']
            flash("Unequipped Bombastic Sweater portrait!")

        # Add a return for both cases
        return render_template('bala_alt1.html', b_set=b_set)





@app.route('/bala_alt2', methods=["GET", "POST"])
def bala2():
    global flags
    b_set = flags.get_data()['b_set']

    if request.method == "GET":
        return render_template('bala_alt2.html', b_set=b_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['b_set'] = 2
            b_set = flags.get_data()['b_set']
            flash("Riptide Aqua portrait equipped! Return to the Members Page and check out bala's new appearance!")
        elif action == "unequip":
            flags.get_data()['b_set'] = 0
            b_set = flags.get_data()['b_set']
            flash("Unequipped Riptide Aqua portrait!")

        # Add a return for both cases
        return render_template('bala_alt2.html', b_set=b_set)




@app.route('/bala_alt3', methods=["GET", "POST"])
def bala3():
    global flags
    b_set = flags.get_data()['b_set']

    if request.method == "GET":
        return render_template('bala_alt3.html', b_set=b_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['b_set'] = 3
            b_set = flags.get_data()['b_set']
            flash("Royal Madness portrait equipped! Return to the Members Page and check out bala's new appearance!")
        elif action == "unequip":
            flags.get_data()['b_set'] = 0
            b_set = flags.get_data()['b_set']
            flash("Unequipped Royal Madness portrait!")

        # Add a return for both cases
        return render_template('bala_alt3.html', b_set=b_set)




@app.route('/unlock_bala',methods=["POST"])
def unlock_bala():
    '''
    Receives input code in order to unlock the alt2 and 3 outfits
    '''
    code = str(request.form.get('costume_unlock')).upper()
    if code == "B2":
        flags.get_data()['bala_alt2'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/bala3imcu/bala_alt2.jpg',
            'caption': 'Riptide Aqua unlocked!'
        })

    if code == "B3":
        flags.get_data()['bala_alt3'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/bala3imcu/bala_alt3.jpg',
            'caption': 'Royal Madness unlocked!'
        })
    else:
        return jsonify({'status': 'fail', 'message': 'Wrong code, try again!'}), 403

    return "Locked. Use the popup to enter passcode."


#====================
#   8. USING456
#====================


@app.route('/using456', methods=["GET"])
def using():
    global flags
    classy_black = flags.get_data()['using_alt2']
    matrix = flags.get_data()['using_alt3']
    if flags.get_data()["using_alt2"] == True and flags.get_data()["using_alt3"] == True:
        flags.get_data()["u_badge"] = True
    return render_template('using.html',using_alt2=classy_black,using_alt3=matrix)


@app.route('/using_alt1', methods=["GET", "POST"])
def using1():
    global flags
    u_set = flags.get_data()['u_set']

    if request.method == "GET":
        return render_template('using_alt1.html', u_set=u_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['u_set'] = 1
            u_set = flags.get_data()['u_set']
            flash("Festive Ninja portrait equipped! Return to the Members Page and check out using's new appearance!")
        elif action == "unequip":
            flags.get_data()['u_set'] = 0
            u_set = flags.get_data()['u_set']
            flash("Unequipped Festive Ninja portrait!")

        # Add a return for both cases
        return render_template('using_alt1.html', u_set=u_set)





@app.route('/using_alt2', methods=["GET", "POST"])
def using2():
    global flags
    u_set = flags.get_data()['u_set']

    if request.method == "GET":
        return render_template('using_alt2.html', u_set=u_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['u_set'] = 2
            u_set = flags.get_data()['u_set']
            flash("Midnight Maestro portrait equipped! Return to the Members Page and check out using's new appearance!")
        elif action == "unequip":
            flags.get_data()['u_set'] = 0
            u_set = flags.get_data()['u_set']
            flash("Unequipped Midnight Maestro portrait!")

        # Add a return for both cases
        return render_template('using_alt2.html', u_set=u_set)




@app.route('/using_alt3', methods=["GET", "POST"])
def using3():
    global flags
    u_set = flags.get_data()['u_set']

    if request.method == "GET":
        return render_template('using_alt3.html', u_set=u_set)

    elif request.method == "POST":
        action = request.form.get("action")
        if action == "equip":
            flags.get_data()['u_set'] = 3
            u_set = flags.get_data()['u_set']
            flash("1x1x1x1 portrait equipped! Return to the Members Page and check out using's new appearance!")
        elif action == "unequip":
            flags.get_data()['u_set'] = 0
            u_set = flags.get_data()['u_set']
            flash("Unequipped 1x1x1x1 portrait!")

        # Add a return for both cases
        return render_template('using_alt3.html', u_set=u_set)




@app.route('/unlock_using',methods=["POST"])
def unlock_using():
    '''
    Receives input code in order to unlock the alt2 and 3 outfits
    '''
    code = str(request.form.get('costume_unlock')).upper()
    if code == "U2":
        flags.get_data()['using_alt2'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/using456/using_alt2.jpg',
            'caption': 'Classy Black unlocked!'
        })

    if code == "U3":
        flags.get_data()['using_alt3'] = True
        return jsonify({
            'status': 'success',
            'image_url': '/static/members/using456/using_alt3.webp',
            'caption': '1x1x1x1 unlocked!'
        })
    else:
        return jsonify({'status': 'fail', 'message': 'Wrong code, try again!'}), 403

    return "Locked. Use the popup to enter passcode."




#===============================
#   10. ROBLOX FORCE AVATAR
#===============================

@app.route('/secret_character',methods=["POST"])
def secret_character():
    ''' 
        Retrieves the passcode to unlock the secret character
        and returns either a successful page or a failed one with hints
    '''
    global flags
    passcode = str(request.form.get("passcode")).upper()    # Auto capitalises the supplied passcode
    if passcode == "GBWN":
        flags.get_data()['unlocked'] = True
        return render_template('secret_character.html')
    else:
        hints = read_txt("hints.txt")
        msg = "Here's a hint: "+hints[random.randint(0,len(hints)-1)]   # Sends a random hint from the array
        return jsonify({'status': 'fail', 'message': 'Wrong code, try again!'}), 403




#Roblox Forc Avatar's page
@app.route('/rforce_avatar', methods=["GET"])
def rforce_avatar():
    return render_template("rforce_avatar.html")





#================
#   11. GAMES     
#================



# @app.route('/costume_game',methods=["GET"])
# def costume_game():
#     '''
#     Shows a list of all the unlocked costumes, cartoonish versions
#     '''
#     global flags
    
#     costumes = []
#     for key in flags.get_data().keys():
#         # If the flag variable is a costume
#         if "_alt" in key:

#             # Setup the name and outfit numbers from each flag
#             name = reverse_truncate[key[0:-5]]
#             number = int(key[-1])

#             # If outfit is locked, the locked image will be displayed
#             if flags.get_data()[key] == False:
#                 outfit = get_character_alt(name,number)
#             else:
#                 # The cartoon version of the outfit is displayed if unlocked
#                 outfit = get_cartoon_costume(name,number)[0]
#             costumes.append(outfit)
    
#     # Corresponding assignments
#     tim1 = costumes[0]
#     tim2 = costumes[1]
#     ellis2 = costumes[2]
#     ellis3 = costumes[3]
#     bala2 = costumes[4]
#     bala3 = costumes[5]
#     using2 = costumes[6]
#     using3 = costumes[7]

#     return render_template("costume_game.html",t1=tim1,t2=tim2,e2=ellis2,e3=ellis3,\
#                            b2=bala2,b3=bala3,u2=using2,u3=using3)






@app.route('/badges',methods=["GET"])
def badges():
    ''' Retrieves the corresponding badges and displays them on badges.html'''
    global flags
    tim_badge = flags.get_data()["t_badge"]
    ellis_badge = flags.get_data()["e_badge"]
    bala_badge = flags.get_data()["b_badge"]
    using_badge = flags.get_data()["u_badge"]

    progress = flags.get_progress()[0]
    return render_template("badges.html",t_badge=tim_badge,e_badge=ellis_badge,b_badge=bala_badge,u_badge=using_badge,progress=float(progress))



#================
#   12. SAVES
#================

# When the user clicks on saves they will be directed to load_save_screen
# Rather than drawing on save file, it now receives updates from flags
class SaveSlot(Flags):
    def __init__(self,name):
        super().__init__()  # Inherit from the Flags objects
        self.data = None
    
    def get_profile(self):
        if self.data is None:
            return [None,None,None,None]
        else:
            self.tim = get_cartoon_costume('timwong',self.data['t_set'])[0]
            self.ellis = get_cartoon_costume('ellisl4d2character',self.data['e_set'])[0]
            self.bala = get_cartoon_costume('bala3imcu',self.data['b_set'])[0]
            self.using = get_cartoon_costume('using456',self.data['u_set'])[0]
            return [self.tim,self.ellis,self.bala,self.using]


test_save_101 = {
        "timwong_alt2" : True,
        "timwong_alt3" : True,
        "ellis_alt2": True,
        "ellis_alt3": True,
        "bala_alt2": True,
        "bala_alt3": True,
        "using_alt2": True,
        "using_alt3": True,
        "unlocked": True,
        "t_badge": True,
        "e_badge": True,
        "b_badge": True,
        "u_badge": True,
        "quiz_badge": True,
        "uploader": True,
        "t_set": 0,
        "e_set": 0,
        "b_set": 0,
        "u_set": 0
        }

test_save_100 = {
        "timwong_alt2" : True,
        "timwong_alt3" : True,
        "ellis_alt2": True,
        "ellis_alt3": True,
        "bala_alt2": True,
        "bala_alt3": True,
        "using_alt2": True,
        "using_alt3": True,
        "unlocked": False,
        "t_badge": True,
        "e_badge": True,
        "b_badge": True,
        "u_badge": True,
        "quiz_badge": True,
        "uploader": True,
        "t_set": 0,
        "e_set": 0,
        "b_set": 0,
        "u_set": 0
        }

# The 5 save slots available to the user
slot1 = SaveSlot("slot1")
slot2 = SaveSlot("slot2")
slot3 = SaveSlot("slot3")
slot4 = SaveSlot("slot4")
slot5 = SaveSlot("slot5")

slots = [slot1,slot2,slot3,slot4,slot5]



curr_action = None
valid_actions = ["load","save","delete","clear","import","export"]    # These actions are chosen at the current_save.html page


@app.route('/load_save_screen',methods=["GET"])
def load_save_screen():
    # This shows the user's progress, and gives them the option to load, save or delete.
    global flags
    tim,ellis,bala,using = flags.get_profile()
    progress,award = flags.get_progress()
    return render_template("current_save.html",tim=tim,ellis=ellis,bala=bala,using=using,progress=float(progress),award=award)



# This function takes in the button value pressed by the user and brings them to save_selection
@app.route('/save_prompt',methods=["POST"])
def save_prompt():

    
    global flags,slot1,slot2,slot3,slot4,slot5,curr_action,valid_actions

    action = request.form.get("action")  # "load", "save", "delete"

    #1. Unsuccessful action, just return back to the same page
    if action not in valid_actions:
        tim,ellis,bala,using = flags.get_profile()
        progress,award = flags.get_progress()
        return render_template("current_save.html",tim=tim,ellis=ellis,bala=bala,using=using,progress=float(progress),award=award)
    
    # Update the global variable to the selected action
    if action in valid_actions:
        curr_action = action

    # Generate the data inside the 5 slots. WIll show up as empty if their data are None
    tim1,ellis1,bala1,using1 = slot1.get_profile()
    tim2,ellis2,bala2,using2 = slot2.get_profile()
    tim3,ellis3,bala3,using3 = slot3.get_profile()
    tim4,ellis4,bala4,using4 = slot4.get_profile()
    tim5,ellis5,bala5,using5 = slot5.get_profile()

    slot1_data = slot1.get_data()
    slot2_data = slot2.get_data()
    slot3_data = slot3.get_data()
    slot4_data = slot4.get_data()
    slot5_data = slot5.get_data()

    progress1,award1 = slot1.get_progress()
    progress2,award2 = slot2.get_progress()
    progress3,award3 = slot3.get_progress()
    progress4,award4 = slot4.get_progress()
    progress5,award5 = slot5.get_progress()
    
    # Go to save selection
    return render_template("save_selection.html",tim1=tim1,ellis1=ellis1,bala1=bala1,using1=using1,\
                            tim2=tim2,ellis2=ellis2,bala2=bala2,using2=using2,\
                            tim3=tim3,ellis3=ellis3,bala3=bala3,using3=using3,\
                            tim4=tim4,ellis4=ellis4,bala4=bala4,using4=using4,\
                            tim5=tim5,ellis5=ellis5,bala5=bala5,using5=using5,\
                            slot1=slot1_data,slot2=slot2_data,slot3=slot3_data,slot4=slot4_data,slot5=slot5_data,\
                            progress1=progress1,progress2=progress2,progress3=progress3,progress4=progress4,progress5=progress5,\
                            award1=award1,award2=award2,award3=award3,award4=award4,award5=award5,curr_action=curr_action)


    
# After choosing the save slot, this function carries out the action chosen by the user
@app.route('/update_save',methods=["POST"])
def update_save():

    global slots,curr_action,flags

    chosen_slot = request.form.get("save_button")   #e.g save1

    if chosen_slot is not None:
        save_no = int(chosen_slot[-1]) - 1 #e.g 1
        curr_slot = slots[save_no]    # this is the actual save object chosen by index


        #1. The slot's data will be transferred over to the global flags
        if curr_action == "load":
            if curr_slot.get_data() != None:    # Important check as the flags might accidentally be set to None and screw up the program
                copy_of_slot = {}
                for key,value in curr_slot.get_data().items():
                    copy_of_slot[key] = value
                flags.update_data(copy_of_slot)
                del copy_of_slot
                curr_slot = None
                curr_action = None


        #2. The slot will store the data from the flags; essentially its a reverse case from load
        elif curr_action == "save":

            copy_of_flags = {}
            for key, value in flags.get_data().items():
                copy_of_flags[key] = value
            curr_slot.update_data(copy_of_flags)
            del copy_of_flags

        #3. Deleting simply just resets the slot's data back to None
        if curr_action == "delete":
            curr_slot.update_data(None)


    tim,ellis,bala,using = flags.get_profile()
    progress,award = flags.get_progress()
    return render_template("current_save.html",tim=tim,ellis=ellis,bala=bala,using=using,progress=float(progress),award=award)

    
# After clicking "Export", "Import" or "Clear", invole this function
@app.route('/update_flags',methods=["POST"])
def update_flags():
    global curr_action, flags
    action = request.form.get("action")
    if action is not None:
        curr_action = action

        #4. Clear means the main flags data is reset to default
        if curr_action == "clear":
            flags.update_data(Flags().get_data())

        #5. Import data from json file
        elif curr_action == "import":
            # Need to add some flask file upload code here
            # flags.import_from_json(filename)
            pass

        #6. Export slot as json file
        elif curr_action == "export":
            # Build JSON in memory and return as download
            payload = json.dumps(flags.get_data(), indent=4, ensure_ascii=False).encode("utf-8")
            filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
            return send_file(
                BytesIO(payload),
                mimetype="application/json; charset=utf-8",
                as_attachment=True,
                download_name=filename
            )


    tim,ellis,bala,using = flags.get_profile()
    progress,award = flags.get_progress()
    return render_template("current_save.html",tim=tim,ellis=ellis,bala=bala,using=using,progress=float(progress),award=award)



# @app.route('/quiz_game',methods=["GET"])
# def quiz_game():
#     ''' Brings the user to the quiz game page'''
#     return render_template('quiz_game.html')


# @app.route('/quiz_result',methods=["POST"])
# def quiz_result():
#     ''' Calculates the score of the quiz results and gives user a badge if full score'''
#     global flags
#     score = 0   # Initialise a score for the correct answers
#     Q1 = request.form["Q1"]
#     Q2 = request.form["Q2"]
#     Q3 = request.form["Q3"]
#     Q4 = request.form["Q4"]
#     Q5 = request.form["Q5"]
#     if Q1 == "220320":
#         score += 1
#     if Q2 == "bala":
#         score += 1
#     if Q3 == "event2":
#         score += 1
#     if Q4 == "061220":
#         score += 1
#     if Q5 == "game4":
#         score += 1
#     if score == 5:
#         flags.get_data()['quiz_badge'] = True
#         msg = "You scored full marks! Well done!"
#         badge = 'Roblox Force Webpage\static\games\rforce_expert.jpg'
#         return render_template('badge.html',msg=msg,badge=badge)
#     msg = f"You scored {score} out of 5. Try again to get full marks!"
#     return render_template("quiz_game.html",msg=msg)





# UPLOAD_FOLDER = 'C:\\Users\\wongc\\OneDrive\\Documents\\Python Project Collection\\Roblox Force Webpage (Portfolio)\\static\\custom_badges'
# ALLOWED_EXTENSIONS = ["JPG","JPEG","PNG"]
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].upper() in ALLOWED_EXTENSIONS





# @app.route('/upload_badge_game',methods=["GET"])
# def upload_badge_game():
#     '''Brings the user to the upload badge page'''
#     return render_template('upload_badge_game.html')


# @app.route('/upload_badge', methods=['POST'])
# def upload_badge():
#     global flags
#     badge = '/static/games/star_badge.jpg'
#     task = "Thanks for uploading your own badge! Here's one for you"
#     if request.method == 'POST':
#         # check if the post request has the file part
#         if 'file' not in request.files:
#             msg="File not deteced"
#             return render_template("upload_badge_game.html",msg=msg)
#         file = request.files['file']
#         if file.filename == '':
#             msg="File has no name"
#             return render_template("upload_badge_game.html",msg=msg)
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             flags.get_data()['uploader'] = True
#             msg2 = "Thank you for submitting your custom badge."
#             return render_template("upload_badge_game.html",msg2=msg2)





'''======================= TUTORIALS =========================='''


@app.route('/tutorial/jetpack', methods=["GET"])
def jetpack():
    return render_template('jetpack_tutorial.html')

@app.route('/tutorial/bombastic', methods=["GET"])
def bombastic():
    return render_template('bombastic_tutorial.html')



app.run(debug=True, port=5017)
