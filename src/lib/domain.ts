export type CropName = 'Cotton' | 'Wheat' | 'Groundnut' | 'Rice';

export type Role = 'farmer' | 'buyer' | 'fpo';
export type Lang = 'en' | 'gu' | 'hi' | 'mr';

export type Crop = {
  id: string;
  name: CropName;
  variety: string;
  quantity: number;
  grade: string;
  parameters: Record<string, number | string>;
  location: string;
  sell_date: string;
  preferred_market?: string;
  notes: string;
  public: boolean;
  photos?: string[];
};

export type Price = {
  market: string;
  district?: string | null;
  state: string;
  crop: string;
  variety: string;
  grade: string;
  min: number;
  max: number;
  price: number;
  date: string;
  arrivals: number | null;
};

export type Feed = {
  status: string;
  source: string;
  source_url?: string;
  date?: string;
  fetched_at?: string;
  message?: string;
  records: any[];
  [key: string]: any;
};

export const crops: CropName[] = [
  'Cotton',
  'Wheat',
  'Groundnut',
  'Rice'
];

export const cities: Record<string, [number, number]> = {
  Surat: [21.1702, 72.8311],
  Ahmedabad: [23.0225, 72.5714],
  Rajkot: [22.3039, 70.8022],
  Vadodara: [22.3072, 73.1812],
  Junagadh: [21.5222, 70.4579],
  Mumbai: [19.076, 72.8777],
  Srinagar: [34.0837, 74.7973]
};

export const rupee = (n: number | undefined | null) =>
  n == null
    ? 'â€”'
    : new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
      }).format(n);

export const today = () =>
  new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(new Date());

export const dateLabel = (date?: string) =>
  date
    ? new Date(date + 'T00:00:00').toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      })
    : 'â€”';

/*
  Static legacy reference removed.
  Live market data now comes from Data.gov.in / AGMARKNET.
  Keep this export so existing imports do not break.
*/
export const reference: Feed = {
  status: 'unavailable',
  source: 'No static reference data',
  message: 'Use latest available Data.gov.in / AGMARKNET market data.',
  records: []
};

export const cropParameters: Record<
  CropName,
  { key: string; label: string; unit: string; max: number }[]
> = {
  Cotton: [
    {
      key: 'moisture_pct',
      label: 'Moisture',
      unit: '%',
      max: 100
    },
    {
      key: 'trash_pct',
      label: 'Trash / foreign matter',
      unit: '%',
      max: 100
    },
    {
      key: 'staple_mm',
      label: 'Staple length',
      unit: 'mm',
      max: 100
    },
    {
      key: 'micronaire',
      label: 'Micronaire',
      unit: '',
      max: 15
    }
  ],

  Wheat: [
    {
      key: 'moisture_pct',
      label: 'Moisture',
      unit: '%',
      max: 100
    },
    {
      key: 'foreign_pct',
      label: 'Foreign matter',
      unit: '%',
      max: 100
    },
    {
      key: 'damaged_pct',
      label: 'Damaged grains',
      unit: '%',
      max: 100
    },
    {
      key: 'test_weight',
      label: 'Test weight',
      unit: 'kg/hl',
      max: 150
    }
  ],

  Groundnut: [
    {
      key: 'moisture_pct',
      label: 'Moisture',
      unit: '%',
      max: 100
    },
    {
      key: 'foreign_pct',
      label: 'Foreign matter',
      unit: '%',
      max: 100
    },
    {
      key: 'damaged_pct',
      label: 'Damaged kernels',
      unit: '%',
      max: 100
    },
    {
      key: 'shelling_pct',
      label: 'Shelling percentage',
      unit: '%',
      max: 100
    },
    {
      key: 'aflatoxin',
      label: 'Aflatoxin (lab result)',
      unit: 'Âµg/kg',
      max: 100000
    }
  ],

  Rice: [
    {
      key: 'moisture_pct',
      label: 'Moisture',
      unit: '%',
      max: 100
    },
    {
      key: 'broken_pct',
      label: 'Broken grains',
      unit: '%',
      max: 100
    },
    {
      key: 'foreign_pct',
      label: 'Foreign matter',
      unit: '%',
      max: 100
    },
    {
      key: 'damaged_pct',
      label: 'Damaged / discoloured grains',
      unit: '%',
      max: 100
    }
  ]
};

export const varieties: Record<CropName, string[]> = {
  Cotton: [
    'Shankar-6',
    'DCH-32',
    'Other / not listed'
  ],

  Wheat: [
    'Lokwan',
    'Sharbati',
    'GW-496',
    'Other / not listed'
  ],

  Groundnut: [
    'G20',
    'GJG-22',
    'Bold',
    'Other / not listed'
  ],

  Rice: [
    'Basmati',
    'IR-64',
    'Sona Masuri',
    'Other / not listed'
  ]
};

export const gradeGuides: Record<CropName, string[]> = {
  Cotton: [
    'Clean, consistent colour and fibre; staple and micronaire measured.',
    'Minor colour or trash variation; disclose measurements.',
    'Noticeable variation or contamination; buyer inspection required.'
  ],

  Wheat: [
    'Uniform, clean grain with minimal visible damage.',
    'Minor variation or damaged grains; record percentages.',
    'More visible defects; buyer must confirm acceptable use.'
  ],

  Groundnut: [
    'Uniform, clean kernels; record moisture and a lab result if available.',
    'Minor size variation or defects; record affected percentage.',
    'Significant visible variation; buyer and laboratory review required.'
  ],

  Rice: [
    'Clean, uniform grains; record moisture and broken-grain percentage.',
    'Some broken or discoloured grains; disclose measured percentages.',
    'More visible damage or mixed grains; buyer inspection required.'
  ]
};

export const fpoSource =
  'https://sfacindia.com/PDFs/List-of-FPO%20identified-by-SFAC/List%20of%20FPOs%20in%20the%20State%20of%20Gujarat.pdf';

export const directoryFpos = [
  {
    id: 'directory-15',
    name: 'Umarpada Pulse Crop Producer Company Limited',
    location: 'Umarpada, Surat',
    crops: 'Cotton, pulses',
    contact: '6352867055',
    members: null,
    services: [],
    verified: false,
    source_url: fpoSource
  },
  {
    id: 'directory-8',
    name: 'Netrang Pulse Crop Producer Company Ltd.',
    location: 'Jhagadia, Bharuch',
    crops: 'Cotton, pulses',
    contact: '9925239376',
    members: null,
    services: [],
    verified: false,
    source_url: fpoSource
  },
  {
    id: 'directory-2',
    name: 'Kankrej Kisan Prducer Company Ltd.',
    location: 'Thara, Banaskantha',
    crops: 'Cotton, wheat, castor, pulses',
    contact: '9712927833',
    members: null,
    services: [],
    verified: false,
    source_url: fpoSource
  }
];

export const transportReference: Feed = {
  status: 'snapshot',
  source: 'FR8',
  fetched_at: '2026-09-19',
  source_url:
    'https://www.fr8.in/transport-service/surat-transport-service/surat-to-mumbai/',
  records: [
    {
      id: 'fr8-1',
      name: 'FR8',
      vehicle: '32ft MXL Container',
      payload_tonnes: 15,
      trip_price: 33000,
      range: 'â‚¹33,000 â€“ â‚¹34,500',
      origin: 'Surat',
      destination: 'Mumbai',
      distance_km: 320
    },
    {
      id: 'fr8-2',
      name: 'FR8',
      vehicle: '32ft SXL Container',
      payload_tonnes: 7,
      trip_price: 23000,
      range: 'â‚¹21,500 â€“ â‚¹25,000',
      origin: 'Surat',
      destination: 'Mumbai',
      distance_km: 320
    },
    {
      id: 'fr8-3',
      name: 'FR8',
      vehicle: '20ft / 22ft / 24ft Container',
      payload_tonnes: 6,
      trip_price: 17000,
      range: 'â‚¹16,225 â€“ â‚¹18,500',
      origin: 'Surat',
      destination: 'Mumbai',
      distance_km: 320
    },
    {
      id: 'fr8-4',
      name: 'FR8',
      vehicle: '19ft Open Truck',
      payload_tonnes: 6,
      trip_price: 20000,
      range: 'â‚¹17,150 â€“ â‚¹22,250',
      origin: 'Surat',
      destination: 'Mumbai',
      distance_km: 320
    }
  ]
};

// Preview-only identifiers also work on the local HTTP preview origin.
export function previewId() {
  return (
    'preview-' +
    Array.from(
      crypto.getRandomValues(new Uint8Array(16)),
      b => b.toString(16).padStart(2, '0')
    ).join('')
  );
}
