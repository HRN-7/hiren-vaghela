import {useEffect,useRef,type ReactNode} from 'react';
import {Sprout,Globe,Info,X,ArrowUpRight,Inbox,LoaderCircle} from 'lucide-react';
import {useLanguage} from '../lib/i18n';
import type {Lang} from '../lib/domain';
export function Brand(){return <a className="brand" href="/"><span className="brand-icon"><Sprout size={25}/></span><span className="brand-name">KrishiLink <b>AI</b></span></a>}
export function Language(){const{lang,setLang}=useLanguage();return <label className="language"><Globe size={17}/><span className="sr-only">Language</span><select value={lang} onChange={e=>setLang(e.target.value as Lang)}><option value="en">English</option><option value="gu">ગુજરાતી</option><option value="hi">हिन्दी</option><option value="mr">मराठी</option></select></label>}
export function Panel({children,className=''}:{children:ReactNode;className?:string}){return <section className={'panel '+className}>{children}</section>}
export function Badge({children,tone='neutral'}:{children:ReactNode;tone?:string}){return <span className={'badge '+tone}>{children}</span>}
export function Note({children,tone='info'}:{children:ReactNode;tone?:string}){return <div className={'note '+tone}><Info size={17}/><span>{children}</span></div>}
export function Empty({title,description,action}:{title:string;description?:string;action?:ReactNode}){const{t}=useLanguage();return <div className="empty"><div className="empty-icon"><Inbox size={25}/></div><h3>{t(title)}</h3>{description&&<p>{t(description)}</p>}{action}</div>}
export function Field({label,children,hint}:{label:string;children:ReactNode;hint?:string}){const{t}=useLanguage();return <label className="field"><span>{t(label)}</span>{children}{hint&&<small>{t(hint)}</small>}</label>}
export function Source({name,url,date}:{name:string;url?:string;date?:string}){const{t}=useLanguage();return <div className="source">{t('Source')}: {url?<a href={url} target="_blank" rel="noreferrer">{name} <ArrowUpRight size={12}/></a>:name}{date&&<span> · {date}</span>}</div>}
export function Modal({title,children,onClose}:{title:string;children:ReactNode;onClose:()=>void}){const ref=useRef<HTMLDialogElement>(null);const{t}=useLanguage();useEffect(()=>{ref.current?.showModal();return()=>ref.current?.close();},[]);return <dialog ref={ref} className="modal" onCancel={onClose} onClick={e=>{if(e.target===e.currentTarget)onClose();}}><div className="modal-head"><h2>{t(title)}</h2><button type="button" className="icon-btn" onClick={onClose} aria-label={t('Close')}><X/></button></div>{children}</dialog>}
export function Busy(){const{t}=useLanguage();return <span className="busy"><LoaderCircle size={18} className="spin"/>{t('Loading…')}</span>}
