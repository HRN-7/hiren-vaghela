/** Calculate using explicitly entered prices and costs in INR/quintal. */
export function calculateNet({price,transport,storage,charges,quantity}) {
 const numbers=[price,transport,storage,charges,quantity].map(Number);
 if(numbers.some(n=>!Number.isFinite(n))||numbers.slice(0,4).some(n=>n<0)||numbers[4]<=0)throw new Error('Enter valid non-negative costs and a quantity greater than zero.');
 const [p,t,s,c,q]=numbers;
 const net=(Math.round(p*100)-Math.round(t*100)-Math.round(s*100)-Math.round(c*100))/100;
 return {net,total:Math.round(net*q*100)/100,cost:t+s+c,gross:p*q};
}
export function rankMarkets(rows){return rows.map(r=>({...r,...calculateNet(r)})).sort((a,b)=>b.net-a.net);}
