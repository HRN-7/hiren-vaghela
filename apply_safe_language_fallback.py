from pathlib import Path

p = Path("src/lib/i18n.tsx")
s = p.read_text(encoding="utf-8")

old = """const Context=createContext({lang:'en' as Lang,setLang:(_l:Lang)=>{},t:(s:string)=>s});
export function LanguageProvider({children}:{children:ReactNode}){const [lang,set]=useState<Lang>(()=>(['en','gu','hi','mr'].includes(localStorage.getItem('krishilink-language')||'')?localStorage.getItem('krishilink-language') as Lang:'en'));useEffect(()=>{document.documentElement.lang=lang},[lang]);const setLang=(l:Lang)=>{set(l);localStorage.setItem('krishilink-language',l);document.documentElement.lang=l;};const t=(s:string)=>lang==='en'?s:catalog[s]?.[{gu:0,hi:1,mr:2}[lang]]||s;return <Context.Provider value={{lang,setLang,t}}>{children}</Context.Provider>}
export const useLanguage=()=>useContext(Context);
"""

new = """const Context=createContext({lang:'en' as Lang,setLang:(_l:Lang)=>{},t:(s:string)=>s});

function brokenTranslation(value:string|undefined){
 if(!value)return true;
 const markers=['àª','à«','à¤','à¥','Ã','Â','â€','â€¦','�'];
 return markers.some(marker=>value.includes(marker));
}

export function LanguageProvider({children}:{children:ReactNode}){
 const [lang,set]=useState<Lang>(()=>{
  const saved=localStorage.getItem('krishilink-language')||'';
  return ['en','gu','hi','mr'].includes(saved)?saved as Lang:'en';
 });

 useEffect(()=>{
  document.documentElement.lang=lang;
 },[lang]);

 const setLang=(l:Lang)=>{
  set(l);
  localStorage.setItem('krishilink-language',l);
  document.documentElement.lang=l;
 };

 const t=(s:string)=>{
  if(lang==='en')return s;
  const index={gu:0,hi:1,mr:2}[lang];
  const translated=catalog[s]?.[index];
  return brokenTranslation(translated)?s:translated;
 };

 return <Context.Provider value={{lang,setLang,t}}>{children}</Context.Provider>;
}

export const useLanguage=()=>useContext(Context);
"""

if old not in s:
    raise SystemExit("Could not find the LanguageProvider block. No file was changed.")

p.write_text(s.replace(old, new, 1), encoding="utf-8", newline="\n")
print("Safe language fallback applied.")
print("Changed ONLY: src/lib/i18n.tsx")
print("Corrupted translations now fall back to clean English instead of mojibake.")
