# Data provenance

| Source | Use and limits |
| --- | --- |
| [AGMARKNET](https://agmarknet.gov.in/daily-price-and-arrival-report) | Supplied Apple report, observed 2026-09-10. Historical reference, not current live prices. |
| [data.gov.in API](https://api.data.gov.in/) | Server-side key required. Current mandi price resource configured in `.env.example`; missing arrival values remain null. |
| [eNAM trade dashboard](https://enam.gov.in/web/dashboard/trade-data) | Official public reference. No undocumented endpoint or fabricated integration claimed. Authorized feed access still needed. |
| [Open-Meteo](https://open-meteo.com/en/docs) | Live current weather and seven-day daily outlook. Source observation time displayed. |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Community locations and map tiles, ODbL attribution displayed. Listings do not establish storage suitability or vacancy. |
| [OSRM](https://project-osrm.org/docs/v5.24.0/api/) | Driving-route estimates from OSM. No real-time traffic, truck restrictions, fuel or toll guarantee. |
| [FR8 Surat–Mumbai](https://www.fr8.in/transport-service/surat-transport-service/surat-to-mumbai/) | Published full-truck rates fetched server-side. Fallback reference retrieved 2026-09-19. Four rows refreshed successfully in verification on 2026-09-20. Confirm quotations and availability with the provider. |
| [VRC Mobility](https://www.vrcmobility.in/platform) | Published platform/API-access reference. Authenticated partner access not supplied. |
| [GoMyTruck](https://gomytruck.com/freight-rate-index/) | Freight benchmark reference, not current vehicle availability. |
| [SFAC Gujarat directory](https://sfacindia.com/PDFs/List-of-FPO%20identified-by-SFAC/List%20of%20FPOs%20in%20the%20State%20of%20Gujarat.pdf) | Historical records 2, 8 and 15. Contacts/services should be reconfirmed. No invented membership/capacity or verified badge. |
| [WDRA](https://wdra.gov.in/) | Storage-directory reference. Current vacancy/tariffs require confirmed operator data. |

## Farm photograph

`public/farm.jpg`: [The Green Field](https://commons.wikimedia.org/wiki/File:The_Green_Field.jpg), Abhijeet Sawant, [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). The UI crops the photo for its layout; attribution remains visible on the login screen. The original image file is retained.

## Feed states

`current` / `published_reference` / `historical` / `estimated` / `unavailable` are distinct. Provider responses and each observation's date are kept visible. Unknown costs are not assumed to be zero for recommendations. Calculator defaults are explicitly an example scenario.

Partner storage records must supply source URL, timestamp, documented cost units and verified availability before automated recommendations can be activated. The existing normalized adapter must be matched to the chosen provider's documented contract; it is not a turnkey integration for an arbitrary vendor.
