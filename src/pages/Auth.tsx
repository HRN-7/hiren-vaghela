import {useEffect,useState,type FormEvent} from 'react';
import {Link,useNavigate,useLocation} from 'react-router-dom';
import {ArrowRight,Check,Leaf,ShieldCheck,Eye,EyeOff,Sprout,Users,Building2} from 'lucide-react';
import {createUserWithEmailAndPassword,signInWithEmailAndPassword,sendPasswordResetEmail,sendEmailVerification,updateProfile,signInWithPopup,GoogleAuthProvider,type User} from 'firebase/auth';
import {auth,authReady} from '../lib/firebase';
import {api} from '../lib/api';
import {useApp,needsEmailVerification} from '../lib/context';
import {useLanguage} from '../lib/i18n';
import {Brand,Language,Field,Note,Busy} from '../components/ui';
import {roleHome,validRole} from '../lib/roles';
import type {Role} from '../lib/domain';
export default function AuthPage(){
 const{t,lang}=useLanguage();const nav=useNavigate();const location=useLocation();const mode=location.pathname.slice(1)||'login';const{user,reload}=useApp();
 const[email,setEmail]=useState('');const[password,setPassword]=useState('');const[name,setName]=useState('');
 const[role,setRole]=useState<Role|null>(()=>{const saved=sessionStorage.getItem('krishilink-role');return validRole(saved)?saved:null;});
 const[phone,setPhone]=useState('');const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[message,setMessage]=useState('');const[show,setShow]=useState(false);
 useEffect(()=>{setError('');setMessage('');},[mode]);
 function selectRole(r:Role){setRole(r);sessionStorage.setItem('krishilink-role',r);setError('');}
 async function finish(u:User){
  if(needsEmailVerification(u)){nav('/verify');return;}
  await u.getIdToken(true);
  try{const profile=await reload();if(role&&profile.role!==role)throw Error('This account belongs to a different role. Select the role used when you registered.');nav(roleHome(profile.role));}
  catch(e:any){if(e.status===404&&role){try{await api('/auth/profile',{method:'POST',body:JSON.stringify({name:u.displayName||name||'KrishiLink User',role,location:'Surat',language:lang})});const profile=await reload();nav(roleHome(profile.role));}catch{nav(roleHome(role,true));}return;}throw e;}
 }
 function fail(e:any){const codes:Record<string,string>={'auth/invalid-credential':'Email or password is incorrect.','auth/email-already-in-use':'This email already has an account. Please sign in.','auth/weak-password':'Password must include 1 capital letter, 1 number and 1 special character, with no spaces.','auth/too-many-requests':'Too many attempts. Please wait and retry.','auth/popup-closed-by-user':'Google sign-in was cancelled.','auth/unauthorized-domain':'Sign-in is not available on this domain yet.','auth/popup-blocked':'Please allow the Google sign-in popup and try again.'};setError(codes[e.code]||e.message||'Unable to sign in. Please try again.');}
 function validateCredentials(){if(!/^[^\s@]+@[^\s@]+\.(com|in)$/i.test(email.trim()))throw Error('Enter a valid email address with .com or .in.');if(credentials&&!/^(?=.{6,30}$)(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9\s])\S+$/.test(password))throw Error('Password must be 6–30 characters and include 1 capital letter, 1 number and 1 special character. Spaces are not allowed.');if(credentials&&!/^\d{10}$/.test(phone))throw Error('Enter exactly 10 digits for your Indian mobile number.');}
 async function submit(e:FormEvent){e.preventDefault();setError('');if(!auth){setError('Sign-in is being prepared.');return;}if(!role&&mode!=='forgot'){setError('Select your role to continue.');return;}setBusy(true);try{
  if(mode==='onboarding'){await api('/auth/profile',{method:'POST',body:JSON.stringify({name:name||user?.displayName||'',role,location:'Surat',language:lang})});const p=await reload();nav(roleHome(p.role));}
  else if(mode==='forgot'){if(!/^[^\s@]+@[^\s@]+\.(com|in)$/i.test(email.trim()))throw Error('Enter a valid email address with .com or .in.');await sendPasswordResetEmail(auth,email);setMessage('If an account exists, a password reset email will arrive shortly.');}
  else {validateCredentials();if(mode==='signup'){const result=await createUserWithEmailAndPassword(auth,email,password);await updateProfile(result.user,{displayName:name});await sendEmailVerification(result.user);nav('/onboarding');}else await finish((await signInWithEmailAndPassword(auth,email,password)).user);}
 }catch(e){fail(e);}finally{setBusy(false);}}
 async function google(){if(!role){setError('Select your role to continue.');return;}if(!auth){setError('Google sign-in needs Firebase configuration. The button is ready once Firebase is connected.');return;}setBusy(true);setError('');try{await finish((await signInWithPopup(auth,new GoogleAuthProvider())).user);}catch(e){fail(e);}finally{setBusy(false);}}
 const credentials=mode==='login'||mode==='signup';
 return <div className="auth-page"><aside className="auth-visual"><img src="/farm.jpg" alt="Green agricultural fields in Gujarat"/><div className="auth-shade"/><Brand/><div className="auth-story"><span className="eyebrow"><Leaf size={16}/>{t('FARMER FIRST. ALWAYS.')}</span><h1>{t('A better market.')}<br/>{t('A better return.')}</h1><p>{t('Compare selling options after transport, storage and market costs.')}</p><div className="auth-proof"><ShieldCheck size={22}/><span>{t('Maximize net realization, not just price.')}</span></div></div><a className="photo-credit" href="https://commons.wikimedia.org/wiki/File:The_Green_Field.jpg" target="_blank" rel="noreferrer">The Green Field Ã‚Â· Abhijeet Sawant Ã‚Â· CC BY-SA 3.0 Ã‚Â· cropped</a></aside><section className="auth-form-side"><header><div className="mobile-brand"><Brand/></div><Language/></header><div className="auth-form"><span className="mini-label">{t('GROW WITH KRISHILINK')}</span><h2>{t(mode==='signup'?'Create your account':mode==='forgot'?'Forgot password?':mode==='verify'?'Verify your email':mode==='onboarding'?'Complete your profile':'Welcome back')}</h2><p className="muted">{t('A little clarity. A better harvest.')}</p>
 {(credentials||mode==='onboarding')&&<fieldset className="role-picker" disabled={busy}><legend>{t('1. Select your role')}</legend><div className="role-options">{([['farmer','Farmer',Sprout],['fpo','FPO',Users],['buyer','Buyer',Building2]] as const).map(([r,label,Icon])=><label key={r} className={role===r?'selected':''}><input type="radio" name="account-role" value={r} checked={role===r} onChange={()=>selectRole(r)}/><Icon size={21}/><span>{t(label)}</span>{role===r&&<Check size={15}/>}</label>)}</div></fieldset>}
 {!authReady&&<Note>{t('Sign-in is being prepared. The preview is available below.')}</Note>}
 {error&&<div role="alert" className="note error">{t(error)}</div>}{message&&<div role="status" className="note success">{t(message)}</div>}
 {mode==='verify'?<div className="stack"><p>{t('Open the verification link in your email, then return here.')}</p><button className="btn" disabled={!user||busy} onClick={async()=>{setBusy(true);try{await user.reload();await finish(user);}catch(e){fail(e);}finally{setBusy(false);}}}>{t('I have verified my email')}<Check size={18}/></button><button className="btn secondary" disabled={!user||busy} onClick={async()=>{try{await sendEmailVerification(user);setMessage('Verification email sent.');}catch(e){fail(e);}}}>{t('Resend verification email')}</button></div>:<>
 <form onSubmit={submit} className="stack"><fieldset className="credential-fields stack" disabled={busy||(!role&&mode!=='forgot')}>
 {credentials&&<legend>{t('2. Your account details')}</legend>}
 {(mode==='signup'||mode==='onboarding')&&<Field label="Full name"><input required minLength={2} maxLength={120} value={name} onChange={e=>setName(e.target.value)} autoComplete="name" placeholder={t('Your full name')}/></Field>}
 {mode!=='onboarding'&&<Field label="Email"><input required type="email" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com"/></Field>}
 {credentials&&<><Field label="Phone Number" hint="10 digits only"><div className="phone-input"><span className="phone-prefix">+91</span><input type="tel" inputMode="numeric" pattern="[0-9]{10}" maxLength={10} value={phone} onChange={e=>setPhone(e.target.value.replace(/\D/g,'').slice(0,10))} autoComplete="tel-national" placeholder="9876543210"/></div></Field><Field label="Password"><div className="password-input"><input required minLength={mode==='signup'?6:1} maxLength={mode==='signup'?30:100} type={show?'text':'password'} value={password} onChange={e=>setPassword(e.target.value.replace(/\s/g,''))} autoComplete={mode==='signup'?'new-password':'current-password'} placeholder={t('Enter your password')}/><button type="button" aria-label={t(show?'Hide password':'Show password')} onClick={()=>setShow(!show)}>{show?<EyeOff size={18}/>:<Eye size={18}/>}</button></div></Field></>}
 {mode==='login'&&<Link to="/forgot" className="text-link right">{t('Forgot password?')}</Link>}
 <button className="btn full" disabled={busy}>{busy?<Busy/>:<>{t(mode==='forgot'?'Send reset link':mode==='signup'?'Sign up':mode==='onboarding'?'Save profile':'Sign in')}<ArrowRight size={17}/></>}</button></fieldset></form>

 {credentials&&<><div className="or"><span>{t('OR')}</span></div><button className="btn google full" onClick={google} disabled={busy||!role}><span className="google-g">G</span>{t('Continue with Google')}</button></>}
 </>}
 <p className="auth-switch">{mode==='login'?<>{t("Don't have an account?")} <Link to="/signup">{t('Sign up')}</Link></>:<Link to="/login">{t('Back to sign in')}</Link>}</p><Link className="preview-link" to={roleHome(role||'farmer',true)}>{t('Explore preview')}<ArrowRight size={16}/></Link></div><footer><span>Ã‚Â© {new Date().getFullYear()} KrishiLink AI</span><Link to="/preview/farmer/support">{t('Support & sources')}</Link></footer></section></div>
}


