# -*- coding: utf-8 -*-
"""GENERATED from the server's exdata.py + company_news.py (do not edit by hand):
the exact rules that decide whether a headline names a company. GitHub applies them as a coarse first filter;
the server re-applies the full rule set (publishers, story de-duplication) before storing anything."""
import re, unicodedata

LEGAL = ['ab', 'adr', 'ads', 'ag', 'aksjeselskap', 'aktiebolag', 'aktiengesellschaft', 'aktieselskab', 'and', 'anonima', 'anonyme', 'as', 'asa', 'azioni', 'berhad', 'bhd', 'bv', 'class', 'co', 'common', 'companies', 'company', 'corp', 'corporation', 'cv', 'de', 'global', 'gmbh', 'group', 'holding', 'holdings', 'inc', 'incorporated', 'kabushiki', 'kaisha', 'kg', 'kgaa', 'kk', 'la', 'limited', 'llc', 'lp', 'ltd', 'naamloze', 'nv', 'nyse', 'of', 'ordinary', 'oyj', 'per', 'plc', 'pt', 'pte', 'pty', 'registered', 'sa', 'sab', 'sarl', 'sas', 'se', 'share', 'shares', 'sociedad', 'societa', 'societe', 'spa', 'stock', 'tbk', 'the', 'vennootschap', 'worldwide']
LEGAL = set(LEGAL)

GENERIC = ['american', 'bank', 'biosciences', 'boston', 'brands', 'care', 'chemical', 'chemicals', 'communications', 'devices', 'electric', 'energy', 'financial', 'first', 'food', 'foods', 'general', 'global', 'health', 'healthcare', 'industrial', 'industries', 'instruments', 'international', 'laboratories', 'labs', 'life', 'materials', 'medical', 'motors', 'national', 'networks', 'new', 'pharmaceutical', 'pharmaceuticals', 'products', 'sciences', 'scientific', 'services', 'software', 'solutions', 'systems', 'technologies', 'technology', 'therapeutics', 'united']
GENERIC = set(GENERIC)


def fold(s):
    """lowercase + strip accents: Nestlé -> nestle, Lagardère -> lagardere"""
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def tokens(s):
    s = fold(s).replace("&", " and ")
    # single letters are punctuation debris from "S.A", "N.V", "A/S"
    return [t for t in re.findall(r"[a-z0-9]+", s) if t not in LEGAL and len(t) >= 2]


def names_company(title, qname):
    """The headline must name THIS company: the full name as a phrase, or every
    distinctive word of it (so 'Eli Lilly' needs both words, and a generic word
    like 'healthcare' or 'boston' can never qualify a headline on its own)."""
    ft = " " + re.sub(r"[^a-z0-9]+", " ", fold(title)) + " "
    phrase = " " + re.sub(r"[^a-z0-9]+", " ", fold(qname)).strip() + " "
    if phrase.strip() and phrase in ft:
        return True
    distinct = [t for t in tokens(qname) if t not in GENERIC and len(t) >= 2]
    return bool(distinct) and all((" " + t + " ") in ft for t in distinct)
