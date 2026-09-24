import {useEffect,lazy,Suspense} from 'react';
import {Routes,Route,Navigate,Outlet,useLocation} from 'react-router-dom';
import {LanguageProvider} from './lib/i18n';
import {AppProvider,useApp,needsEmailVerification} from './lib/context';
import {roleHome,rolePaths} from './lib/roles';
import type {Role} from './lib/domain';
import {Busy} from './components/ui';
import Layout from './components/Layout';
import AuthPage from './pages/Auth';
const FarmerDashboard=lazy(()=>import('./pages/Dashboard'));
const BuyerDashboard=lazy(()=>import('./pages/RoleDashboards').then(m=>({default:m.BuyerDashboard})));
const FpoDashboard=lazy(()=>import('./pages/RoleDashboards').then(m=>({default:m.FpoDashboard})));
const Crops=lazy(()=>import('./pages/Crops').then(m=>({default:m.Crops})));
const AddCrop=lazy(()=>import('./pages/Crops').then(m=>({default:m.AddCrop})));
const Markets=lazy(()=>import('./pages/Markets'));
const NetCalculator=lazy(()=>import('./pages/Decisions').then(m=>({default:m.NetCalculator})));
const Recommendations=lazy(()=>import('./pages/Decisions').then(m=>({default:m.Recommendations})));
const Buyers=lazy(()=>import('./pages/Network').then(m=>({default:m.Buyers})));
const Fpos=lazy(()=>import('./pages/Network').then(m=>({default:m.Fpos})));
const Supply=lazy(()=>import('./pages/Transactions').then(m=>({default:m.AvailableSupply})));
const Purchases=lazy(()=>import('./pages/Transactions').then(m=>({default:m.Purchases})));
const FpoManagement=lazy(()=>import('./pages/RoleDashboards').then(m=>({default:m.FpoManagement})));
const FarmerRequests=lazy(()=>import('./pages/RoleDashboards').then(m=>({default:m.FarmerRequests})));
const Storage=lazy(()=>import('./pages/Services').then(m=>({default:m.Storage})));
const Transport=lazy(()=>import('./pages/Services').then(m=>({default:m.Transport})));
const Forecasts=lazy(()=>import('./pages/Misc').then(m=>({default:m.Forecasts})));
const Profile=lazy(()=>import('./pages/Misc').then(m=>({default:m.Profile})));
const Support=lazy(()=>import('./pages/Misc').then(m=>({default:m.Support})));
function Protected(){const{user,profile,loading}=useApp();if(loading)return <div className="empty"><Busy/></div>;if(!user)return <Navigate to="/login" replace/>;if(needsEmailVerification(user))return <Navigate to="/verify" replace/>;if(!profile)return <Navigate to="/onboarding" replace/>;return <Outlet/>;}
function LegacyRedirect(){const{profile,demoRole}=useApp();const{pathname}=useLocation();const preview=pathname.startsWith('/preview');const role:Role=preview?demoRole:profile?.role||'farmer';const path=pathname.split('/').slice(2).join('/')||'dashboard';return <Navigate to={(preview?'/preview':'/app')+'/'+role+'/'+(rolePaths[role].includes(path)?path:'dashboard')} replace/>;}
function roleRoutes(role:Role){return <><Route index element={<Navigate to="dashboard" replace/>}/><Route path="dashboard" element={role==='farmer'?<FarmerDashboard/>:role==='buyer'?<BuyerDashboard/>:<FpoDashboard/>}/>{role==='farmer'&&<><Route path="crops" element={<Crops/>}/><Route path="crops/new" element={<AddCrop/>}/><Route path="markets" element={<Markets/>}/><Route path="recommendations" element={<Recommendations/>}/><Route path="calculator" element={<NetCalculator/>}/><Route path="buyers" element={<Buyers/>}/><Route path="storage" element={<Storage/>}/><Route path="transport" element={<Transport/>}/><Route path="fpos" element={<Fpos/>}/><Route path="forecasts" element={<Forecasts/>}/></>}{role==='buyer'&&<><Route path="buyers" element={<Buyers/>}/><Route path="supply" element={<Supply/>}/></>}{role!=='fpo'&&<Route path="purchases" element={<Purchases/>}/>} {role==='fpo'&&<><Route path="fpos" element={<FpoManagement/>}/><Route path="requests" element={<FarmerRequests/>}/></>}<Route path="profile" element={<Profile/>}/><Route path="support" element={<Support/>}/><Route path="*" element={<Navigate to="../dashboard" replace/>}/></>}
function ScrollReset(){const{pathname}=useLocation();useEffect(()=>{window.scrollTo(0,0)},[pathname]);return null;}
export default function App(){return <LanguageProvider><ScrollReset/><AppProvider><Suspense fallback={<div className="empty"><Busy/></div>}><Routes><Route path="/" element={<AuthPage/>}/>{['login','signup','forgot','verify','onboarding'].map(p=><Route key={p} path={'/'+p} element={<AuthPage/>}/>)}{(['farmer','buyer','fpo'] as Role[]).map(r=><Route key={r} path={'/preview/'+r} element={<Layout role={r}/>}>{roleRoutes(r)}</Route>)}<Route path="/preview/*" element={<LegacyRedirect/>}/><Route element={<Protected/>}>{(['farmer','buyer','fpo'] as Role[]).map(r=><Route key={r} path={'/app/'+r} element={<Layout role={r}/>}>{roleRoutes(r)}</Route>)}<Route path="/app/*" element={<LegacyRedirect/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes></Suspense></AppProvider></LanguageProvider>}
