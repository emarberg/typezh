import csv 
import os
from os import system
from pathlib import Path
from collections import OrderedDict
import pyperclip
import random
import readline

import webbrowser
import urllib.parse

from simplifier import simplify, is_simplified, is_traditional


TRADITIONAL_MODE = 0
SIMPLIFIED_MODE = 1
BOTH_MODE = 2


def clear_screen():
    # Use 'cls' for Windows, 'clear' for POSIX systems (Linux/macOS)
    os.system('cls' if os.name == 'nt' else 'clear')


def translate_with_google(text, sl='auto', tl='en'):
    """
    Opens Google Translate in the browser with input text.
    sl: source language (default auto)
    tl: target language (default english)
    """
    # URL encode the text to handle spaces and special characters
    encoded_text = urllib.parse.quote(text)
    
    # Construct the URL
    url = f"https://translate.google.com/?sl={sl}&tl={tl}&text={encoded_text}&op=translate"
    
    # Open in default web browser
    webbrowser.open(url)


class SystemCallError(Exception):
    pass


def systemcall(command):
    exit_code = system(command)
    if exit_code != 0:
        raise SystemCallError


class Manager:

    PUNCTUATION = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`、﹐{|}~，。！：°（）－．／﹗﹣～﹖；？＂《》「」『』・–—‘’“”•…‧«»%％'

    def speak(self, s, temp=True):
        if not self.muted:
            #system('say -v %s ' % voice + s)
            
            try:
                if temp:
                    if self.temp_sound != s:
                        systemcall('edge-tts --text "%s" --write-media sounds/temp.mp3 >/dev/null 2>&1; afplay sounds/temp.mp3 >/dev/null 2>&1' % s)
                        self.temp_sound = s
                    else:
                        system('afplay sounds/temp.mp3')
                else:
                    file_name = "sounds/%s.mp3" % s
                    file_path = Path(file_name)

                    if not file_path.exists():
                        systemcall('edge-tts --text "%s" --write-media %s >/dev/null 2>&1; afplay %s >/dev/null 2>&1' % (s, file_name, file_name))
                    else:
                        system('afplay %s' % file_name)
            except SystemCallError:
                system('say -v Meijia ' + s)

    def is_valid_sentence(self, s):
        chars = set(s) - set(self.PUNCTUATION)
        if any(ord(c) > ord('龟') for c in chars):
            return False
        if self.mode == TRADITIONAL_MODE and not is_traditional(s):
            return False
        if self.mode == SIMPLIFIED_MODE and not is_simplified(s):
            return False
        return True

    def __init__(self, profile, mode=TRADITIONAL_MODE, muted=False):
        self.SENTENCES_FILE = 'sentences/sentences_zh.csv'
        self.TRANSLATIONS_FILE = 'sentences/translations_zh.csv'

        self.mode = mode
        self.muted = muted
        self.new_translations = []
        self.setup_csv(profile)
        self.read_sentences()

        self.quit = False
        self.temp_sound = ''

    def setup_csv(self, profile):
        Path("./profiles/" + profile).mkdir(parents=True, exist_ok=True)
        self.file = "./profiles/" + profile + "/characters.csv"
        try:
            with open(self.file) as _:
                pass
        except IOError:
            Path(self.file).touch()
            with open(self.file, 'a', newline='\n') as csvfile:
                writer = csv.writer(csvfile, delimiter='\t', quotechar='|')
                writer.writerow(['zh', 'eng'])

    def read_sentences(self):
        self.zh_dict = {}
        self.eng_dict = {}

        self.zh_sentences = []
        self.eng_sentences = []

        with open(self.SENTENCES_FILE, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                zh = row[0]
                if not self.is_valid_sentence(zh):
                    continue
                if zh:
                    self.zh_sentences.append(zh)
                    self.zh_dict[zh] = '' 

        Path(self.TRANSLATIONS_FILE).touch()
        with open(self.TRANSLATIONS_FILE, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t', quotechar='|')
            for row in reader:
                eng, zh = row
                if zh in self.zh_dict:
                    self.zh_dict[zh] = eng

        for zh, eng in self.zh_dict.items():
            if eng:
                print(zh)
                print(eng)
                print()
        input('')



    def save(self):
        with open(self.TRANSLATIONS_FILE, 'a', newline='\n') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t', quotechar='|') 
            for zh, eng in self.new_translations:
                if eng:
                    writer.writerow([eng, zh])

    def run(self):
        self.new_translations = []
        while not self.quit:
            try:
                self.review()
            except KeyboardInterrupt:
                print()
                self.quit = True
        self.save()
        print()

    def get_sentence(self):
        return random.choice(self.zh_sentences)

    def get_translation(self, sentence):
        translation = self.zh_dict[sentence]
        if translation != '':
            return translation

    def add_translation(self, sentence):
        clear_screen()
        print()
        print(sentence)
        print()
        print('add a translation / press enter to open Google translate')
        print()      
        s = input('')
        if s == '':
            translate_with_google(sentence, sl='zh', tl='en')
            clear_screen()
            print()
            print(sentence)
            print()
            print('add a translation:')
            print()
            s = input('')
        else:
            print()
            confirm = input('confirm add [y/n]: ')
            if confirm != 'y':
                s = ''
        if s:
            self.new_translations.append((sentence, s))

    def matches(self, sentence, received):
        a = tuple(s for s in sentence if s not in self.PUNCTUATION)
        b = tuple(s for s in received if s not in self.PUNCTUATION)
        return a == b

    def print_sentence(self, sentence):
        clear_screen()
        print()
        print(sentence)
        print()

    def extend_match(self, sentence, base, s):
        ell = len(base)
        for i in range(ell, len(s)):
            if i >= len(sentence):
                break
            a, b = s[i], sentence[i]
            if (a == b) or (a in self.PUNCTUATION and b in self.PUNCTUATION):
                base += b
            else:
                break
        return base

    def review(self):
        aloud = False
        sentence = self.get_sentence()

        base = ''
        while True:
            pyperclip.copy(sentence[len(base):len(base) + 1])
            self.print_sentence(sentence)
            print(base, end='')

            if aloud:
                self.speak(sentence[len(base):])
            
            s = input()

            if s == 'q' or s == 'quit':
                self.quit = True
                break
            
            if s == 'skip':
                break
            
            if s == '':
                aloud = True
                continue
                        
            s = base + s
            base = self.extend_match(sentence, base, s)

            if self.matches(sentence, s):
                self.speak(sentence, temp=False)
                pyperclip.copy(sentence)
                translation = self.get_translation(sentence)
                if translation is None:
                    self.add_translation(sentence)
                else:
                    print()
                    print(translation)
                    print()
                    s = input('')
                break
            else:
                aloud = True


def main():
    manager = Manager('default')
    manager.run()


if __name__ == '__main__':
    main()