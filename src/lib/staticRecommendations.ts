import type {Crop} from './domain';
import type {MarketChoice,MarketFeed} from './marketFlow';

const SOURCE_URL='https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi';

export function buildStaticMarketFeed(crop:Crop,storageDays=0):MarketFeed{
  const date=new Date().toISOString().slice(0,10);

  const records:any[]=[
    {
      id:'demo-dehgam',
      market:'Dehgam APMC',
      district:'Gandhinagar',
      state:'Gujarat',
      crop:crop.name,
      commodity:crop.name,
      variety:crop.variety||'Other',
      grade:crop.grade||'A',
      price:2797,
      min:2770,
      max:2825,
      date,
      distance_km:41.3,
      straight_distance_km:34.7,
      variety_match:'Demo crop match',
      grade_verified:true,
      grade_compatibility:'verified',
      demo_transport_cost:68,
      demo_storage_rate:3,
      demo_market_charges:18,
      demo_other_costs:7,
      source:'AGMARKNET demo snapshot',
      source_url:SOURCE_URL,
      distance_note:'Estimated demo road distance.',
      ai_trend:{status:'estimated',signal:'stable',change_pct:1.1,grade_specific:false}
    },
    {
      id:'demo-rekhiyal',
      market:'Dehgam(Rekhiyal) APMC',
      district:'Gandhinagar',
      state:'Gujarat',
      crop:crop.name,
      commodity:crop.name,
      variety:crop.variety||'Other',
      grade:crop.grade||'A',
      price:2750,
      min:2725,
      max:2775,
      date,
      distance_km:26.4,
      straight_distance_km:23.5,
      variety_match:'Demo crop match',
      grade_verified:true,
      grade_compatibility:'verified',
      demo_transport_cost:48,
      demo_storage_rate:3,
      demo_market_charges:17,
      demo_other_costs:6,
      source:'AGMARKNET demo snapshot',
      source_url:SOURCE_URL,
      distance_note:'Estimated demo road distance.',
      ai_trend:{status:'estimated',signal:'stable',change_pct:0.8,grade_specific:false}
    },
    {
      id:'demo-viramgam',
      market:'Viramgam APMC',
      district:'Ahmedabad',
      state:'Gujarat',
      crop:crop.name,
      commodity:crop.name,
      variety:crop.variety||'Other',
      grade:crop.grade||'A',
      price:2780,
      min:2630,
      max:2930,
      date,
      distance_km:61.4,
      straight_distance_km:55.5,
      variety_match:'Demo crop match',
      grade_verified:true,
      grade_compatibility:'verified',
      demo_transport_cost:92,
      demo_storage_rate:3,
      demo_market_charges:16,
      demo_other_costs:7,
      source:'AGMARKNET demo snapshot',
      source_url:SOURCE_URL,
      distance_note:'Estimated demo road distance.',
      ai_trend:{status:'estimated',signal:'stable',change_pct:1.4,grade_specific:false}
    },
    {
      id:'demo-jetpur',
      market:'Jetpur APMC',
      district:'Rajkot',
      state:'Gujarat',
      crop:crop.name,
      commodity:crop.name,
      variety:crop.variety||'Other',
      grade:crop.grade||'A',
      price:2825,
      min:2675,
      max:2940,
      date,
      distance_km:270.5,
      straight_distance_km:233.7,
      variety_match:'Demo crop match',
      grade_verified:true,
      grade_compatibility:'verified',
      demo_transport_cost:240,
      demo_storage_rate:3,
      demo_market_charges:20,
      demo_other_costs:10,
      source:'AGMARKNET demo snapshot',
      source_url:SOURCE_URL,
      distance_note:'Estimated demo road distance.',
      ai_trend:{status:'estimated',signal:'stable',change_pct:1.7,grade_specific:false}
    }
  ];

  const storage=records.map(r=>({
    id:`storage-${r.id}`,
    market_id:r.id,
    name:'Demo dry storage',
    rate_per_quintal_day:r.demo_storage_rate,
    minimum_days:1,
    source:'Demo estimate',
    source_url:SOURCE_URL,
    updated_at:date
  }));

  const transport=records.flatMap(r=>[
    {
      id:`transport-${r.id}`,
      market_id:r.id,
      storage_id:null,
      vehicle:'10 t truck',
      name:'Demo transporter',
      capacity_quintals:100,
      rate_per_km:15,
      source:'Demo estimate',
      source_url:SOURCE_URL,
      updated_at:date
    },
    {
      id:`transport-storage-${r.id}`,
      market_id:r.id,
      storage_id:`storage-${r.id}`,
      vehicle:'10 t truck',
      name:'Demo transporter',
      capacity_quintals:100,
      rate_per_km:15,
      source:'Demo estimate',
      source_url:SOURCE_URL,
      updated_at:date
    }
  ]);

  return {
    status:'available',
    records,
    context:{crop,static_demo:true},
    services:{
      transport,
      storage,
      charges:[],
      message:'Demo selling costs are used for Net Realization ranking.'
    },
    snapshot_id:`static-demo-${crop.id}-${storageDays}`,
    expires_at:'2099-12-31T23:59:59Z',
    message:'Demo mandi snapshot ranked using estimated complete selling costs.',
    source:'AGMARKNET demo snapshot',
    source_url:SOURCE_URL,
    storage_days:storageDays,
    search_limited:false,
    date
  } as MarketFeed;
}

export function buildStaticComparison(
  crop:Crop,
  feed:MarketFeed,
  selections:MarketChoice[],
  storageDays=0
){
  const ids=new Set(selections.map(s=>s.market_id));

  const ranking=(feed.records as any[])
    .filter(r=>ids.has(r.id))
    .map(r=>{
      const transportCost=Number(r.demo_transport_cost||0);
      const storageCost=storageDays>0
        ? Number(r.demo_storage_rate||0)*storageDays
        : 0;
      const marketCharges=Number(r.demo_market_charges||0);
      const otherCosts=Number(r.demo_other_costs||0);

      const net=Number((
        Number(r.price)-
        transportCost-
        storageCost-
        marketCharges-
        otherCosts
      ).toFixed(2));

      const total=Number((net*Number(crop.quantity||0)).toFixed(2));

      const breakdown:any[]=[
        {
          label:'Transport',
          per_quintal:transportCost,
          source:'Demo estimate',
          source_url:SOURCE_URL,
          date:r.date,
          trips:1,
          distance_km:r.distance_km
        }
      ];

      if(storageCost>0){
        breakdown.push({
          label:'Storage',
          per_quintal:storageCost,
          source:'Demo estimate',
          source_url:SOURCE_URL,
          date:r.date,
          billed_days:storageDays
        });
      }

      breakdown.push(
        {
          label:'Market charges',
          per_quintal:marketCharges,
          source:'Demo estimate',
          source_url:SOURCE_URL,
          date:r.date
        },
        {
          label:'Other applicable costs',
          per_quintal:otherCosts,
          source:'Demo estimate',
          source_url:SOURCE_URL,
          date:r.date
        }
      );

      return {
        ...r,
        transport_cost:transportCost,
        storage_cost:storageCost,
        market_charges:marketCharges,
        other_costs:otherCosts,
        net_per_quintal:net,
        total_expected:total,
        missing:[],
        transport:{vehicle:'10 t truck',name:'Demo transporter'},
        storage:storageDays>0?{name:'Demo dry storage'}:null,
        breakdown
      };
    })
    .sort((a,b)=>b.net_per_quintal-a.net_per_quintal)
    .map((r,index)=>({...r,rank:index+1}));

  return {
    status:'estimated',
    ranking,
    best_market_id:ranking[0]?.id||null,
    expires_at:'2099-12-31T23:59:59Z',
    message:'Best option is selected by highest estimated Net Realization per quintal.',
    price_warning:'Demo snapshot: confirm actual mandi prices and selling costs before a real transaction.',
    timing_warning:''
  };
}
