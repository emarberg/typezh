import csv 
import os
from os import system
from pathlib import Path
from collections import OrderedDict
import pyperclip
import random
import readline
from simplifier import simplify, is_simplified, is_traditional


TRADITIONAL_MODE = 0
SIMPLIFIED_MODE = 1
BOTH_MODE = 2


def clear_screen():
    # Use 'cls' for Windows, 'clear' for POSIX systems (Linux/macOS)
    os.system('cls' if os.name == 'nt' else 'clear')


class Manager:

    PUNCTUATION = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`、﹐{|}~，。！：°（）－．／﹗﹣～﹖；？＂《》「」『』・–—‘’“”•…‧«»%％'
    SENTENCES_FILE = 'data/sentences_zh.csv'

    def speak(self, s, voice='Meijia'):
        if not self.muted:
            #system('say -v %s ' % voice + s)
            if self.lastwritten != s:
                self.lastwritten = s
                system('edge-tts --text "%s" --write-media temp.mp3; afplay temp.mp3' % s)
            else:
                system('afplay temp.mp3')

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
        self.mode = mode
        self.muted = muted
        self.added = []
        self.setup_csv(profile)
        self.read_data()

        self.quit = False
        self.lastwritten = ''

    def setup_csv(self, profile):
        Path("./profiles/" + profile).mkdir(parents=True, exist_ok=True)
        self.file = "./profiles/" + profile + "/vocabulary.csv"
        try:
            with open(self.file) as _:
                pass
        except IOError:
            Path(self.file).touch()
            with open(self.file, 'a', newline='\n') as csvfile:
                writer = csv.writer(csvfile, delimiter='\t', quotechar='|')
                writer.writerow(['zh', 'eng'])

    def read_data(self):
        self.zh_dict = {}
        self.eng_dict = {}

        self.zh_sentences = []
        self.eng_sentences = []

        with open(self.SENTENCES_FILE, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                zh, eng = row
                if not self.is_valid_sentence(zh):
                    continue
                if zh:
                    self.zh_dict[zh] = eng
                    self.zh_sentences.append(zh)        
                if eng:
                    self.eng_dict[end] = zh
                    self.eng_sentences.append(eng)

    def write_data(self, row):
        with open(self.file, 'a', newline='\n', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t', quotechar='|')
            writer.writerow(row)

    def run(self):
        self.added = []
        while not self.quit:
            try:
                self.review()
            except KeyboardInterrupt:
                print()
                self.quit = True
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
        print('add a translation:')
        print()      
        s = input('')
        if s:
            print()
            print('add? (y/n)')
            print()
            a = input('')
            if a and a[0] == 'y':
                self.added = [(sentence, s)]

    def matches(self, sentence, received):
        a = tuple(s for s in sentence if s not in self.PUNCTUATION)
        b = tuple(s for s in received if s not in self.PUNCTUATION)
        return a == b

    def print_sentence(self, sentence):
        clear_screen()
        print()
        print(sentence)
        print()

    def extend_base(self, sentence, base, s):
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
            base = self.extend_base(sentence, base, s)

            if self.matches(sentence, s):
                self.speak(sentence)
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