import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateNet,rankMarkets} from '../src/lib/calculations.mjs';
test('subtracts all per-quintal costs before multiplying by quantity',()=>{assert.deepEqual(calculateNet({price:2250,transport:80,storage:25,charges:75,quantity:50}),{net:2070,total:103500,cost:180,gross:112500});});
test('ranks net return rather than gross market price',()=>{const rows=rankMarkets([{name:'Higher gross',price:5500,transport:350,storage:0,charges:150,quantity:50},{name:'Higher net',price:5350,transport:180,storage:0,charges:120,quantity:50}]);assert.equal(rows[0].name,'Higher net');assert.equal(rows[0].net,5050);});
test('shows losses and rejects invalid costs and zero quantity',()=>{assert.equal(calculateNet({price:100,transport:110,storage:0,charges:0,quantity:2}).net,-10);for(const invalid of [NaN,Infinity,-1])assert.throws(()=>calculateNet({price:100,transport:invalid,storage:0,charges:0,quantity:2}));assert.throws(()=>calculateNet({price:100,transport:0,storage:0,charges:0,quantity:0}));});
