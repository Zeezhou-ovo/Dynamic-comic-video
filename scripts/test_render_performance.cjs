// Run with a compiled CommonJS copy of assets/remotion/src/performance.ts.
const assert=require('node:assert/strict');
const p=require(process.argv[2]);
const keys=[{frame:0,x:0,y:0,rotation:0,opacity:1},{frame:10,x:10,y:0,rotation:30,opacity:1}];
assert.equal(p.partValue(20,keys,'rotation'),30);
assert.equal(p.partValue(5,keys,'x','ease-in-out'),5);
assert.ok(p.partValue(2,keys,'x','ease-out')>2);
const speech={speaker:'cat',closed_asset:'closed',open_asset:'open',shape_assets:{small:'small'}};
const cues=[{speaker:'cat',start_frame:5,end_frame:8,mouth_shape_frames:['closed','small','open']}];
assert.equal(p.mouthAsset(4,speech,cues),'closed');
assert.equal(p.mouthAsset(5,speech,cues),'closed');
assert.equal(p.mouthAsset(6,speech,cues),'small');
assert.equal(p.mouthAsset(8,speech,cues),'closed');
assert.equal(p.mouthAsset(6,speech,cues,[{speaker:'cat',start_frame:6,end_frame:7,shape:'closed'}]),'closed');
const events=[{layer_id:'eye',pose_asset:'surprise',start_frame:3,end_frame:6}];
assert.equal(p.expressionAsset(5,'eye',events),'surprise');
assert.equal(p.expressionAsset(6,'eye',events),undefined);
console.log('PASS: easing, silence, authored mouth and expression restoration');
