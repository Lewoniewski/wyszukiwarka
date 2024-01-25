from flask import Flask, request, redirect
import urllib.request, re, morfeusz2, requests, json
app = Flask(__name__, static_folder='statyczne')
morf=morfeusz2.Morfeusz()

wersja="0.14"

def szukamy_miesiac(tokeny):
    mies={}
    #wczytujemy do słownika możliwe nazwy miesięcy i odpowiednie wartości dla adresu URL
    with open('inne/miesiace.txt','r',encoding='utf-8') as plik:
        for linijka in plik:
            p=linijka.strip().split("\t")
            #jeżeli nie ma co najmniej 2 elementów (kolumn) -> nie przechodzimy dalej
            if len(p)<2: continue
            mies[p[0]]=p[1]
    w=""
    for k,v in mies.items():
        if k in tokeny:
            w=v
            break
    return w


def szukamy_temat(tokeny):
    tematy={}

    #wczytujemy do słownika możliwe nazwy tematów i odpowiednie wartości dla adresu URL
    with open('inne/tematy.txt','r',encoding='utf-8') as plik:
        for linijka in plik:
            p=linijka.strip().split("\t")
            #jeżeli nie ma co najmniej 2 elementów (kolumn) -> nie przechodzimy dalej
            if len(p)<2: continue
            tematy[p[0]]=p[1]
            
    w="top" #domyślna wartość, jeżeli nie znajdziemy tematu
    for k,v in tematy.items():
        if k in tokeny:
            w=v
            break
    return w

            
@app.route("/", methods=['POST', 'GET'])
def main():
    #wczytujemy szablon dla strony głównej
    with open('szablony/main.html','r',encoding='utf-8') as plik:
        strona=plik.read().replace("{ver}",wersja)

    with open('inne/przyklady.txt','r',encoding='utf-8') as plik:
        przyklady=plik.read().splitlines()

    #generujemy treść dla strony domyślnej (głównej)
    wynik='<div class="ramka2">Przykłady zapytań:</div><ul>'
    for przyklad in przyklady:
        wynik+='<li><a href="?zapytanie='+przyklad+'">'+przyklad+'</a></li>'
    wynik+="</ul>"
    
    z="" #domyślne zapytanie (puste)
    

    #jeżeli zapytanie nie jest puste
    if request.args.get("zapytanie") is not None:

        #bierzemy wartość przekazaną od formularza wyszukiwarki
        z=request.values['zapytanie']

        #sprawdzamy, czy zapytanie dotyczy konkretnego tytułu
        if "analiza:" in z.lower() or "pl.wikipedia.org/wiki/" in z:

            if "analiza:" in z.lower():
                artykul=z.split(":")[1].strip().replace(" ","_")
            else:
                artykul=z.split("pl.wikipedia.org/wiki/")[1]

            return redirect("/analiza/"+artykul, code=302)
                

        else:

            #usuwamy znaki interpunkcyjne (warto dodać jeszcze inne) 
            for pun in ['.',',','!','?',':',';','-']:
                z=z.replace(pun,'')

            #otrzymujemy unikatowe tokeny z zapytania (przed tym jeszcze "zmniejszamy litery")
            tok=set(z.lower().split(" "))

            #przy użyciu oddzielnej funkcji (opisana wyżej) szukamy w zapytaniu słowa, które wskazuje na miesiąc
            mi=szukamy_miesiac(tok)

            #przy użyciu oddzielnej funkcji (opisana wyżej) szukamy tematu
            temat=szukamy_temat(tok) #domyślną wartością będzie "top"

            print (temat)

            #szukamy rok
            rok=re.findall(" (2[0-9][0-9][0-9])",z)

                    
            #jeżeli zdajdziemy rok i miesiąc, to bierzemy stronę z datą
            if len(rok)>0 and mi!="": 
                rok=rok[0]
                url="https://pl.wikirank.net/"+temat+"/"+rok+"-"+mi
                if temat=="top":
                    #sprawdźmy jeszcze czy chodzi o polską wersję
                    if "polski" in tok or "polska" in tok or "polsce" in tok or "polskim" in tok or "polacy" in tok or "polskie" in tok:
                        url="https://pl.wikirank.net/"+temat+"/pl/"+rok+"-"+mi
            else:
                #jeżeli nie ma roku, ale jest miesiąc, przyjmujemy 2021
                if mi!="": 
                    rok="2021"
                    url="https://pl.wikirank.net/"+temat+"/"+rok+"-"+mi
                else:
                    #jeżeli nie ma roku i nie ma miesiąca
                    #najpierw sprawdźmy czy chodzi o polską wersję
                    if "polski" in tok or "polska" in tok or "polsce" in tok or "polskim" in tok or "polacy" in tok or "polskie" in tok:
                        url="https://pl.wikirank.net/"+temat+"/pl"
                    else:
                        url="https://pl.wikirank.net/"+temat
        

        if "popularn" in z.lower() or "top " in z.lower() or len(rok)>0 or mi!="" or temat!="top":
                
            page = urllib.request.urlopen(url)
            kod=page.read().decode("utf-8")

            sz=re.findall('<td><a href=([^>]+)>([^<]+)</a>', kod) #szukamy na stronie nazw
            lista=[]
            for el in sz:
                #jeżeli jest wersja polskojęzyczna, to podać link do strony z analizą
                if '/pl/' in el[0]: lista.append('<a href="/analiza/'+el[1].replace(' ','_')+'">'+el[1]+'</a>')
                else: lista.append(el[1])

            wynik='<div class="ramka2"><a href="/">Strona główna</a> :: '+z+'</div>'
            wynik+='<ol><li>'+'</li><li>'.join(lista)+'</li></ol>'
            wynik+='<p class="source">Źródło: <a href="'+url+'">'+url+'</a></p>'

        else:
            wynik='<div class="ramka2"><a href="/">Strona główna</a> :: '+z+'</div>'
            wynik+='<p>Niestety, na podstawie podanego zapytania nic nie zostało odnalezione. Sprawdź, czy wszystkie słowa zostały poprawnie napisane. Można spróbować użyć innych słów kluczowych. Przykłady:</p>'
            wynik+='<ul>'
            for przyklad in przyklady:
                wynik+='<li><a href="?zapytanie='+przyklad+'">'+przyklad+'</a></li>'
            wynik+='</ul>'
        
    return strona.replace("{z}",z).replace("{wynik}",wynik)


@app.route('/analiza/<zap>')
def zapytanie(zap):
    
    zap=zap.replace("_"," ")
    
    #wczytujemy szablon dla strony, która ma pokazać analizę tekstu wybranego artykułu Wikipedii
    with open('szablony/analiza.html','r',encoding='utf-8') as plik:
        strona=plik.read().replace("{ver}",wersja).replace("{title}",zap)

    stopslowa=set()
    with open('inne/stopslowa.txt','r',encoding='utf-8') as plik:
        for line in plik:
            stopslowa.add(line.strip())
        
    parametry={
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exlimit": "max",
            "explaintext":1,
            "redirects":1,
            "titles": zap}

    response = requests.get('https://pl.wikipedia.org/w/api.php',parametry)
    #print (response.status_code)
    code=response.content.decode('utf-8')
    data=json.loads(code)
    
    pagid=list(data["query"]["pages"])[0]

    #sprawdzamy, czy możemy uzyskać dane (czy podany artykuł Wikipedii istnieje)
    try:
        text=data["query"]["pages"][pagid]["extract"]
    except:
        with open('szablony/main.html','r',encoding='utf-8') as plik:
            strona=plik.read().replace("{ver}",wersja)
        return strona.replace("{z}",zap).replace('{wynik}','<div class="ramka2"><a href="/">Strona główna</a> :: '+zap+'</div><p>Niestety, tego artykułu nie ma w Polskojęzycznej Wikipedii ;( </p>')


    tf={}
    sumatagi={}
    sumatagirozd={}
    #wymieniamy tagi, które nas interesują (nie bierzemy wszustkich)
    #opis skrótów: http://nkjp.pl/poliqarp/help/ense2.html
    #nie wszystkie skróty zostały uwzględnione
    jakietagi={"subst":"rzeczowniki","adj":"przymiotniki","prep":"przyimki",
               "fin":"czasowniki","conj":"spójniki", #"ppron3":"zaimki","ppron12":"zaimki",
               "adv":"przysłówki","comp":"spójniki","ger":"czasowniki",
               "praet":"czasowniki","inf":"czasowniki","depr":"rzeczowniki",
               "pred":"przymiotniki","ppas":"czasowniki","impt":"czasowniki"} 
    
    kolory={"czasowniki":"A00000","przyimki":"A0A000","przymiotniki":"00A000",
            "przysłówki":"00A0A0","rzeczowniki":"0000A0","spójniki":"A000A0"}
    cssnazwy={"czasowniki":"czasowniki","przyimki":"przyimki","przymiotniki":"przymiotniki",
            "przysłówki":"przyslowki","rzeczowniki":"rzeczowniki","spójniki":"spojniki"}
    
    kolorowyabstrakt=[]
    kolorowyabstraktids=set()
    tokeny_czescimowy={}

    for num,xx in enumerate(re.split('\n==[^=]',text)):
        #dla każdego rozdziału do badanego tokena przypisujemy unikatowe tagi z pierwszej cześci
        tagi={}

        if num==0:
            nzw="Strzeszczenie"
            txt=xx
        else:
            r=re.split('[^=]==[^=]?\n',xx)
            if len(r)<2: continue
            nzw=r[0]
            txt=r[1]
        txt=txt.replace("=","").replace("\t"," ").replace("\n"," ").replace("  "," ").replace("  "," ")
        if nzw not in sumatagirozd:
            sumatagirozd[nzw]={}
        an=morf.analyse(txt)
        idslowa=set() #unikatowe id
        idslowa2=set() #dla słownika TF, dla jednego słowa mogą być różne (np. Poznania => poznanie, Poznań)
        #wybrane czesci mowy dla tokenów
        
        for a,b,c in an:
            
            if c[2]=='interp' or c[2]=='dig' or c[2]=='romandig':
                #zezwalamy tylko dla kolorowego abstraktu, żeby nie "stracić" liczb i innych sybmoli
                if num==0:
                    if a not in kolorowyabstraktids:
                        kolorowyabstrakt.append(c[0])
                        kolorowyabstraktids.add(a)
                continue

            cc=c[2].split(":")[0]
            if a not in tagi: tagi[a]=set()
            if cc in jakietagi:
                formapodstawowa=c[1].split(":")[0]
                if formapodstawowa not in tokeny_czescimowy:
                    tokeny_czescimowy[formapodstawowa]=jakietagi[cc]
                tagi[a].add(jakietagi[cc])
                if num==0:
                    if a not in kolorowyabstraktids:
                        kolorowyabstrakt.append('<span class="'+cssnazwy[jakietagi[cc]]+'">'+c[0]+'</span>')
                        kolorowyabstraktids.add(a)
            else:
                if num==0:
                    if a not in kolorowyabstraktids:
                        kolorowyabstrakt.append(c[0])
                        kolorowyabstraktids.add(a)
            
            idslowa.add(a)
            idslowa2.add(str(a)+"::"+c[1])
        for slowo in idslowa2:
            d=slowo.split("::")[1].split(":")[0]
            tf[d]=tf.get(d,0)+1

        for k,v in tagi.items():
            for vv in v:
                sumatagi[vv]=sumatagi.get(vv,0)+1
                sumatagirozd[nzw][vv]=sumatagirozd[nzw].get(vv,0)+1

    dataexport=[]

    count=0        
    for w in sorted(tf, key=tf.get, reverse=True):
        if w.lower() in stopslowa: continue
        count+=1
        if count>250: break #limit na liczbę słów w chmurzę słów
        try: dataexport.append({"tag":w,"weight":tf[w],"color":"am5.color(0x"+kolory[tokeny_czescimowy[w]]+")"})
        except: dataexport.append({"tag":w,"weight":tf[w],"color":"am5.color(0x000000)"})

    dane=json.dumps(dataexport).replace('"tag":','tag:').replace('"weight":','weight:').replace('"color":','color:').replace('"am5.color(','am5.color(').replace(')"',')')

    dataexport2=[]
    for w in sorted(sumatagi.keys()):
        dataexport2.append({"name":w,"value":sumatagi[w],"itemStyle":{"color":"#"+kolory[w]}})

    dane2=json.dumps(dataexport2).replace('"name":','name:').replace('"value":','value:').replace('"color":','color:').replace('"itemStyle":','itemStyle:')

    naglowektabeli=[]
    for w in sorted(sumatagi.keys()):
        naglowektabeli.append('<span class='+cssnazwy[w]+'>'+w+'</span>')
    tabela='<table style="width:100%;border: 1px solid black;"><tr><th style="width:40%;">Nazwa rozdziału</th><th>'+'</th><th>'.join(naglowektabeli)+'</th></tr>'
    for rozd, var in sumatagirozd.items():
        tabela+='<tr><td>'+rozd+'</td>'
        for w in sorted(sumatagi.keys()):
            if w in var: tabela+='<td class="cnt">'+str(var[w])+'</td>'
            else: tabela+='<td class="cnt">0</td>'
        tabela+='</td>'
    tabela+='</table>'

    tresc='<div class="ramka"><a href="/">System Wyszukiwaczy</a> :: Analiza popularnych słów oraz części mowy artykułu "<a href="https://pl.wikipedia.org/wiki/'+zap+'" target="_blank">'+zap+'</a>" z polskojęzycznej Wikipedii.</div>'
    #dzielimy abstrakt przed i po 100 słowami
    przed=" ".join(kolorowyabstrakt[:100])
    po=""
    if len(kolorowyabstrakt)>100:
        po='<span id="dots">...</span><span id="more">'+' '.join(kolorowyabstrakt[100:])+'</span> <button onclick="wiecejMniej()" id="guzikWiecej">Więcej &rarr;</button>'
    tresc+='<p>'+przed+' '+po+'</p>'
    return strona.replace("{!dane!}",dane).replace("{!dane2!}",dane2).replace('{tresc}',tresc).replace('{tabela}',tabela)

if __name__ == "__main__":
    app.run(debug=False)
