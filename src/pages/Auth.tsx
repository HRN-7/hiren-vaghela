import {useEffect,useRef,useState,type FormEvent} from 'react';
import {Link,useNavigate,useLocation} from 'react-router-dom';
import {ArrowRight,Check,Leaf,Phone,ShieldCheck,Eye,EyeOff,Sprout,Users,Building2} from 'lucide-react';
import {createUserWithEmailAndPassword,signInWithEmailAndPassword,sendPasswordResetEmail,sendEmailVerification,updateProfile,signInWithPopup,GoogleAuthProvider,RecaptchaVerifier,signInWithPhoneNumber,linkWithPhoneNumber,type ConfirmationResult,type User} from 'firebase/auth';
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
 const[phone,setPhone]=useState('');const[otp,setOtp]=useState('');const[confirmation,setConfirmation]=useState<ConfirmationResult|null>(null);const[busy,setBusy]=useState(false);const[error,setError]=useState('');const[message,setMessage]=useState('');const[show,setShow]=useState(false);const recaptcha=useRef<RecaptchaVerifier|null>(null);
 useEffect(()=>{setError('');setMessage('');},[mode]);
 useEffect(()=>()=>{recaptcha.current?.clear();recaptcha.current=null;},[]);
 function selectRole(r:Role){setRole(r);sessionStorage.setItem('krishilink-role',r);setError('');}
 async function finish(u:User){
  if(needsEmailVerification(u)){nav('/verify');return;}
  await u.getIdToken(true);
  try{const profile=await reload();if(role&&profile.role!==role)throw Error('This account belongs to a different role. Select the role used when you registered.');nav(roleHome(profile.role));}
  catch(e:any){if(e.status===404){nav('/onboarding');return;}throw e;}
 }
 function fail(e:any){const codes:Record<string,string>={'auth/invalid-credential':'Email or password is incorrect.','auth/email-already-in-use':'This email already has an account. Please sign in.','auth/weak-password':'Use at least 8 characters for your password.','auth/too-many-requests':'Too many attempts. Please wait and retry.','auth/popup-closed-by-user':'Google sign-in was cancelled.','auth/invalid-verification-code':'The OTP is incorrect. Please try again.','auth/code-expired':'The OTP has expired. Request a new one.','auth/unauthorized-domain':'Sign-in is not available on this domain yet.','auth/credential-already-in-use':'This phone number belongs to another account. Sign in to that account.'};setError(codes[e.code]||e.message||'Unable to sign in. Please try again.');}
 function verifier(){if(!auth)throw Error('Sign-in is being prepared.');if(!recaptcha.current)recaptcha.current=new RecaptchaVerifier(auth,'recaptcha',{size:'normal'});return recaptcha.current;}
 function validPhone(){if(!/^\+[1-9]\d{7,14}$/.test(phone))throw Error('Enter your phone number with country code, for example +91 followed by 10 digits.');}
 async function phoneLogin(){if(!auth||!role)return;setBusy(true);setError('');try{validPhone();setConfirmation(await signInWithPhoneNumber(auth,phone,verifier()));setMessage('OTP sent. Check your phone.');}catch(e){fail(e);recaptcha.current?.clear();recaptcha.current=null;}finally{setBusy(false);}}
 async function verifyOtp(){if(!confirmation)return;setBusy(true);setError('');try{const result=await confirmation.confirm(otp);setConfirmation(null);setOtp('');await finish(result.user);}catch(e){fail(e);}finally{setBusy(false);}}
 async function submit(e:FormEvent){e.preventDefault();setError('');if(!auth)return;if(!role&&mode!=='forgot'){setError('Select your role to continue.');return;}setBusy(true);try{
  if(mode==='onboarding'){await api('/auth/profile',{method:'POST',body:JSON.stringify({name:name||user?.displayName||'',role,location:'Surat',language:lang})});const p=await reload();nav(roleHome(p.role));}
  else if(mode==='forgot'){await sendPasswordResetEmail(auth,email);setMessage('If an account exists, a password reset email will arrive shortly.');}
  else if(mode==='signup'){
   if(phone)validPhone();
   const result=await createUserWithEmailAndPassword(auth,email,password);await updateProfile(result.user,{displayName:name});await sendEmailVerification(result.user);
   if(phone){try{setConfirmation(await linkWithPhoneNumber(result.user,phone,verifier()));setMessage('Verify your phone with the OTP, then verify the link sent to your email.');}catch(e){setMessage('Your email account was created. Verify your email, then sign in. Phone linking was not completed.');fail(e);}}
   else nav('/verify');
  }else await finish((await signInWithEmailAndPassword(auth,email,password)).user);
 }catch(e){fail(e);}finally{setBusy(false);}}
 async function google(){if(!auth||!role)return;setBusy(true);setError('');try{await finish((await signInWithPopup(auth,new GoogleAuthProvider())).user);}catch(e){fail(e);}finally{setBusy(false);}}
 const credentials=mode==='login'||mode==='signup';
 return <div className="auth-page"><aside className="auth-visual"><img src="/farm.jpg" alt="Green agricultural fields in Gujarat"/><div className="auth-shade"/><Brand/><div className="auth-story"><span className="eyebrow"><Leaf size={16}/>{t('FARMER FIRST. ALWAYS.')}</span><h1>{t('A better market.')}<br/>{t('A better return.')}</h1><p>{t('Compare selling options after transport, storage and market costs.')}</p><div className="auth-proof"><ShieldCheck size={22}/><span>{t('Maximize net realization, not just price.')}</span></div></div><a className="photo-credit" href="https://commons.wikimedia.org/wiki/File:The_Green_Field.jpg" target="_blank" rel="noreferrer">The Green Field · Abhijeet Sawant · CC BY-SA 3.0 · cropped</a></aside><section className="auth-form-side"><header><div className="mobile-brand"><Brand/></div><Language/></header><div className="auth-form"><span className="mini-label">{t('GROW WITH KRISHILINK')}</span><h2>{t(mode==='signup'?'Create your account':mode==='forgot'?'Forgot password?':mode==='verify'?'Verify your email':mode==='onboarding'?'Complete your profile':'Welcome back')}</h2><p className="muted">{t('A little clarity. A better harvest.')}</p>
 {(credentials||mode==='onboarding')&&<fieldset className="role-picker" disabled={busy||!!confirmation}><legend>{t('1. Select your role')}</legend><div className="role-options">{([['farmer','Farmer',Sprout],['fpo','FPO',Users],['buyer','Buyer',Building2]] as const).map(([r,label,Icon])=><label key={r} className={role===r?'selected':''}><input type="radio" name="account-role" value={r} checked={role===r} onChange={()=>selectRole(r)}/><Icon size={21}/><span>{t(label)}</span>{role===r&&<Check size={15}/>}</label>)}</div></fieldset>}
 {!authReady&&<Note>{t('Sign-in is being prepared. The preview is available below.')}</Note>}
 {error&&<div role="alert" className="note error">{t(error)}</div>}{message&&<div role="status" className="note success">{t(message)}</div>}
 {mode==='verify'?<div className="stack"><p>{t('Open the verification link in your email, then return here.')}</p><button className="btn" disabled={!user||busy} onClick={async()=>{setBusy(true);try{await user.reload();await finish(user);}catch(e){fail(e);}finally{setBusy(false);}}}>{t('I have verified my email')}<Check size={18}/></button><button className="btn secondary" disabled={!user||busy} onClick={async()=>{try{await sendEmailVerification(user);setMessage('Verification email sent.');}catch(e){fail(e);}}}>{t('Resend verification email')}</button></div>:<>
 <form onSubmit={submit} className="stack"><fieldset className="credential-fields stack" disabled={busy||!!confirmation||(!role&&mode!=='forgot')}>
 {credentials&&<legend>{t('2. Your account details')}</legend>}
 {(mode==='signup'||mode==='onboarding')&&<Field label="Full name"><input required minLength={2} maxLength={120} value={name} onChange={e=>setName(e.target.value)} autoComplete="name" placeholder={t('Your full name')}/></Field>}
 {mode!=='onboarding'&&<Field label="Email"><input required type="email" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com"/></Field>}
 {credentials&&<><Field label="Phone Number" hint="Include country code, e.g. +91"><div className="phone-input"><input type="tel" value={phone} onChange={e=>setPhone(e.target.value)} autoComplete="tel" placeholder="+91"/>{mode==='login'&&<button type="button" className="text-link" disabled={!authReady||!phone} onClick={phoneLogin}><Phone size={14}/>{t('Send OTP')}</button>}</div></Field><Field label="Password"><div className="password-input"><input required minLength={mode==='signup'?8:1} type={show?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} autoComplete={mode==='signup'?'new-password':'current-password'} placeholder={t('Enter your password')}/><button type="button" aria-label={t(show?'Hide password':'Show password')} onClick={()=>setShow(!show)}>{show?<EyeOff size={18}/>:<Eye size={18}/>}</button></div></Field></>}
 {mode==='login'&&<Link to="/forgot" className="text-link right">{t('Forgot password?')}</Link>}
 <button className="btn full" disabled={busy||!authReady}>{busy?<Busy/>:<>{t(mode==='forgot'?'Send reset link':mode==='signup'?'Sign up':mode==='onboarding'?'Save profile':'Sign in')}<ArrowRight size={17}/></>}</button></fieldset></form>
 <div id="recaptcha"/>
 {confirmation&&<form className="otp-form stack" onSubmit={e=>{e.preventDefault();verifyOtp();}}><Field label="OTP"><input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={otp} onChange={e=>setOtp(e.target.value)} autoComplete="one-time-code"/></Field><button className="btn" disabled={busy}>{t('Verify OTP')}</button><button className="text-link" type="button" onClick={()=>{setConfirmation(null);setOtp('');recaptcha.current?.clear();recaptcha.current=null;}}>{t('Use another number')}</button></form>}
 {credentials&&<><div className="or"><span>{t('OR')}</span></div><button className="btn google full" onClick={google} disabled={busy||!authReady||!role||!!confirmation}><span className="google-g">G</span>{t('Continue with Google')}</button></>}
 </>}
 <p className="auth-switch">{mode==='login'?<>{t("Don't have an account?")} <Link to="/signup">{t('Sign up')}</Link></>:<Link to="/login">{t('Back to sign in')}</Link>}</p><Link className="preview-link" to={roleHome(role||'farmer',true)}>{t('Explore preview')}<ArrowRight size={16}/></Link></div><footer><span>© {new Date().getFullYear()} KrishiLink AI</span><Link to="/preview/farmer/support">{t('Support & sources')}</Link></footer></section></div>
}
