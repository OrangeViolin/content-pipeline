import assert from 'node:assert/strict';
import test from 'node:test';
import { findNonCdnImages, isOfficialWechatCdn, planImageInsertions } from './wechat-api.ts';

const cdn = 'https://mmbiz.qpic.cn/example/0';

test('official CDN is https on the WeChat image hosts', () => {
  assert.equal(isOfficialWechatCdn(cdn), true);
  assert.equal(isOfficialWechatCdn('https://mmbiz.qlogo.cn/example/0'), true);
  assert.equal(isOfficialWechatCdn('http://mmbiz.qpic.cn/example/0'), false);
  assert.equal(isOfficialWechatCdn('data:image/png;base64,aaaa'), false);
  assert.equal(isOfficialWechatCdn('file:///tmp/a.png'), false);
  assert.equal(isOfficialWechatCdn('https://example.com/a.png'), false);
});

test('non-CDN images stay visible to the draft gate', () => {
  const html = `<img src="file:///tmp/a.png"><img src="${cdn}">`;
  assert.deepEqual(findNonCdnImages(html), ['file:///tmp/a.png']);
});

test('missing paragraph anchors are not filled by list order', () => {
  assert.deepEqual(planImageInsertions('<p>甲</p>', ['a.png']).missing, ['a.png']);
  assert.deepEqual(planImageInsertions('<!-- IMAGE:a.png --><p>甲</p>', ['a.png']).missing, []);
  assert.deepEqual(planImageInsertions('<!-- IMAGE:a --><p>甲</p>', ['a.png']).missing, []);
});
