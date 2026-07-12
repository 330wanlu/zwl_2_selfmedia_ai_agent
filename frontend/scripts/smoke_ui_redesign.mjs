/**
 * 前端科技感改版冒烟 + 主链路功能自测
 * 前置：后端 :8000、前端 :5173 已启动
 */
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.join(__dirname, 'out')
fs.mkdirSync(OUT, { recursive: true })

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:5173'
const results = []

function pass(name) {
  results.push(`PASS ${name}`)
  console.log(`PASS ${name}`)
}

function fail(name, err) {
  results.push(`FAIL ${name}: ${err}`)
  console.error(`FAIL ${name}: ${err}`)
}

async function clickEnabled(locator, label) {
  await locator.waitFor({ state: 'visible', timeout: 120_000 })
  for (let i = 0; i < 60; i++) {
    if (await locator.isEnabled()) break
    await locator.page().waitForTimeout(1000)
  }
  if (!(await locator.isEnabled())) throw new Error(`按钮仍 disabled: ${label}`)
  await locator.click()
  console.log(`clicked: ${label}`)
}

function topicCard(page) {
  return page
    .locator('.ant-card')
    .filter({ has: page.locator('.ant-card-head-title', { hasText: /选题决策/ }) })
    .first()
}

function contentCard(page) {
  return page
    .locator('.ant-card')
    .filter({ has: page.locator('.ant-card-head-title', { hasText: /文案审核/ }) })
    .first()
}

function imageCard(page) {
  return page
    .locator('.ant-card')
    .filter({ has: page.locator('.ant-card-head-title', { hasText: '图片审核' }) })
    .first()
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage()
page.setDefaultTimeout(30_000)

try {
  // 1. 列表页品牌与创建区
  await page.goto(`${FRONT}/tasks`)
  await page.getByText('Beauty Agent').first().waitFor({ state: 'visible' })
  await page.getByText('任务列表').first().waitFor({ state: 'visible' })
  await page.getByText('创建并开始').waitFor({ state: 'visible' })
  await page.getByText('SYSTEM ONLINE').waitFor({ state: 'visible' })
  await page.locator('.app-shell__grid').waitFor({ state: 'attached' })
  pass('list page branding & create UI')

  // 2. 代理 API
  const listRes = await page.request.get(`${FRONT}/api/v1/tasks`)
  if (!listRes.ok()) throw new Error(`list status ${listRes.status()}`)
  const tasks = await listRes.json()
  if (!Array.isArray(tasks) || tasks.length === 0) throw new Error('no tasks')
  pass(`proxy list tasks (${tasks.length})`)

  const completed = tasks.find((t) => t.status === 'completed')
  if (!completed) throw new Error('no completed task')

  // 3. 已完成任务详情
  await page.goto(`${FRONT}/tasks/${completed.id}`)
  await page.getByText('任务详情').first().waitFor({ state: 'visible' })
  await page.getByText('流水线进度').waitFor({ state: 'visible' })
  await page.getByRole('button', { name: '查看内容包' }).waitFor({ state: 'visible' })
  pass('detail page completed task')

  // 4. 内容包页
  await page.goto(`${FRONT}/tasks/${completed.id}/package`)
  await page.getByText('小红书内容包').first().waitFor({ state: 'visible' })
  await page.getByRole('button', { name: '一键复制文字' }).waitFor({ state: 'visible' })
  await page.getByRole('button', { name: '批量下载图片' }).waitFor({ state: 'visible' })
  await page.getByText('导出 JSON').waitFor({ state: 'visible' })
  await page.locator('.ant-card-head-title', { hasText: '标题' }).waitFor({ state: 'visible' })
  await page.locator('.ant-card-head-title', { hasText: '正文' }).waitFor({ state: 'visible' })
  await page.locator('.ant-card-head-title', { hasText: '话题标签' }).waitFor({ state: 'visible' })
  await page.locator('.ant-card-head-title', { hasText: '图片组' }).waitFor({ state: 'visible' })
  const imgs = await page.locator('.ant-image img').count()
  if (imgs < 1) throw new Error('no package images')
  pass(`package page content & actions (images=${imgs})`)

  // 5. 创建任务 → 选题
  await page.goto(`${FRONT}/tasks`)
  await page.getByPlaceholder(/例如/).fill('敏感肌温和洁面推荐-UI自测')
  await page.getByRole('button', { name: '创建并开始' }).click()
  await page.waitForURL(/\/tasks\/[0-9a-f-]+/, { timeout: 20_000 })
  const taskId = page.url().split('/').pop()
  console.log('created task', taskId)

  await page
    .locator('.ant-card-head-title', { hasText: /选题决策/ })
    .waitFor({ state: 'visible', timeout: 360_000 })
  await topicCard(page).getByRole('radio').first().click()
  await clickEnabled(topicCard(page).getByRole('button', { name: '确认选题' }), '确认选题')
  pass('create task + select topic')

  // 6. 文案审核
  await page
    .locator('.ant-card-head-title', { hasText: /文案审核/ })
    .waitFor({ state: 'visible', timeout: 360_000 })
  await clickEnabled(
    contentCard(page).locator('button.ant-btn-primary').filter({ hasText: /通\s*过/ }),
    '通过',
  )
  pass('approve content')

  // 7. 图片审核
  await page
    .locator('.ant-card-head-title', { hasText: '图片审核' })
    .waitFor({ state: 'visible', timeout: 600_000 })
  await clickEnabled(imageCard(page).getByRole('button', { name: '全部通过' }), '全部通过')
  pass('approve images')

  // 8. 完成 → 内容包
  await page.getByRole('button', { name: '查看内容包' }).waitFor({ state: 'visible', timeout: 360_000 })
  await page.getByRole('button', { name: '查看内容包' }).click()
  await page.waitForURL(/\/package/)
  await page.getByText('小红书内容包').first().waitFor({ state: 'visible' })
  await page.getByRole('button', { name: '一键复制文字' }).click()
  pass('new task package reachable')

  await page.screenshot({ path: path.join(OUT, 'ui_redesign_smoke.png'), fullPage: true })
  pass('screenshot saved')
} catch (e) {
  fail('flow', e?.message || String(e))
  await page.screenshot({ path: path.join(OUT, 'ui_redesign_fail.png'), fullPage: true }).catch(() => {})
} finally {
  await browser.close()
  const summary = results.join('\n')
  fs.writeFileSync(path.join(OUT, 'ui_redesign_smoke.log'), summary, 'utf8')
  console.log('---')
  console.log(summary)
  if (results.some((r) => r.startsWith('FAIL'))) process.exit(1)
}
