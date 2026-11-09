# book.stenaline.pl GraphQL cheatsheet

Endpoint: `POST /graphql` (same origin, session cookie from the funnel). Content-type JSON,
body `{operationName, query, variables}`.

## Round-trip (cruise pair) search

```graphql
query S($salesOwnerId: ID!, $languageId: ID!, $currencyId: ID!, $routeId: ID!,
        $date: LocalDate!, $productCode: String!,
        $numPassengers: [NumberOfPassengerCategoryInput!]!, $offerCode: String) {
  searchSailings {
    searchRoundTripPairs(
      salesOwnerId: $salesOwnerId languageId: $languageId currencyId: $currencyId
      routeId: $routeId date: $date productCode: $productCode
      numPassengers: $numPassengers numVehiclesOfTypes: [] numTrailersOfTypes: []
      numberOfPets: 0 offerCode: $offerCode
      currentSalesChannelCode: "PIB" originalSalesChannelCode: "PIB"
    ) {
      __typename
      ... on SearchRoundTripPairsSuccess {
        pairs {
          soldOut
          totalPrice { amount }
          packagePricing {
            __typename
            ... on RoundTripDiscountedPrice {
              priceAfterDiscount { amount } priceBeforeDiscount { amount }
            }
          }
          outward  { sailing { departureDate localDepartureTime }
                     product { offerCodeStatus { __typename } } }
          homeward { sailing { departureDate localDepartureTime } }
        }
      }
      ... on SearchRoundTripPairsError { errorMessages { technicalMessage } }
    }
  }
}
```

Variables (2 adults, Gdynia→Karlskrona, PLN):

```json
{
  "salesOwnerId": "16", "languageId": "PL", "localeId": "pl-PL", "currencyId": "PLN",
  "routeId": "GDKA", "date": "2026-10-08", "productCode": "CRUSKG2",
  "offerCode": "GDYNIA100",
  "numPassengers": [{"numberSelected": 2, "passengerCategory": "ADULT",
                     "typeGenericId": "866B4D8A-8B67-48BF-85CC-BB72C019683C"}]
}
```

`__typename` outcomes: `SearchRoundTripPairsSuccess` | `SearchRoundTripPairsNotFound`
(no sailing that day) | `SearchRoundTripPairsError` (bad productCode).

## Known codes

- Routes: `GDKA` Gdynia→Karlskrona, `KAGD` reverse; `RSTB`/`TBRS`, `KIGO`/`GOKI`,
  `VENY`/`NYVE`, `GOFR`/`FRGO`, `LITR`/`TRLI`, `HOHA`/`HAHO`, `CNBF`/`BFCN`,
  `FIRO`/`ROFI`, `BFLP`/`LPBF`, `DBHH`/`HHDB`.
- Sales owner: `16` = Stena Line Polska. Sales channel: `PIB`.
- Products on GDKA: `CRUSKG1` = Rejs 24h, `CRUSKG2` = Rejs 36h.
  (`CRUSKG2C` is the marketing/widget code; the API returns NotFound for it.)
- Passenger typeGenericIds: ADULT `866B4D8A-8B67-48BF-85CC-BB72C019683C`.

## Async scan pattern (avoids browser_console timeout)

```js
(()=>{window.__s={};window.__d=false;
 (async()=>{const d0=new Date('2026-10-08T00:00:00Z');
  for(let i=0;i<65;i++){const d=new Date(d0.getTime()+i*864e5).toISOString().slice(0,10);
   const r=await fetch('/graphql',{method:'POST',headers:{'content-type':'application/json'},
     body:JSON.stringify({operationName:'S',query:Q,variables:{...base,date:d}})});
   const j=await r.json(); window.__s[d]=summarise(j);}
  window.__d=true;})(); return 'go';})()
```

Then `sleep 70` in the terminal and read `window.__s` in a second `browser_console` call.
