import test from 'node:test';
import assert from 'node:assert/strict';
import {roleHome,rolePaths,validRole} from '../src/lib/roles.ts';
test('each account role resolves to a distinct dashboard',()=>{
 assert.deepEqual(['farmer','buyer','fpo'].map(r=>roleHome(r)),['/app/farmer/dashboard','/app/buyer/dashboard','/app/fpo/dashboard']);
 assert.equal(validRole('admin'),false);
});
test('farmer tools do not appear in buyer or FPO workspaces',()=>{
 for(const r of ['buyer','fpo'])for(const path of ['crops','crops/new','markets','recommendations','calculator','forecasts','storage','transport'])assert.equal(rolePaths[r].includes(path),false);
 assert.equal(rolePaths.buyer.includes('supply'),true);
 assert.equal(rolePaths.fpo.includes('requests'),true);
 assert.equal(rolePaths.farmer.includes('supply'),false);
});
