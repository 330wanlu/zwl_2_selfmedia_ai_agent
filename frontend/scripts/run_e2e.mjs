/**
 * 阶段 3 前端 E2E：运营人员不经 Swagger，在页面上走完全流程。
 *
 * 前置：后端 :8000、前端 :5173 已启动
 * 用法（frontend 目录）:
 *   npm run test:e2e
 *   # 从挂起任务续跑（省额度）:
 *   $env:RESUME_TASK_ID="uuid"; $env:RESUME_FROM="content"; npm run test:e2e
 *
 * RESUME_FROM: topic | content | images | package
 * 日志：scripts/out/stage3_e2e.log
 */
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.join(__dirname, 'out')
fs.mkdirSync(OUT, { recursive: true })
const LOG = path.join(OUT, 'stage3_e2e.log')

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:5173'
const DIRECTION = process.env.E2E_DIRECTION || '平价口红试色推荐'
const RESUME_TASK_ID = process.env.RESUME_TASK_ID || ''
const RESUME_FROM = process.env.RESUME_FROM || 'start'

const lines = []
function log(msg) {
  lines.push(`[${new Date().toISOString()}] ${msg}`)
  console.log(msg)
}

async function waitForText(page, text, timeout = 360_000) {
  await page.getByText(text).first().waitFor({ state: 'visible', timeout })
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

function topicCard(page) {
  return page
    .locator('.ant-card')
    .filter({ has: page.locator('.ant-card-head-title', { hasText: /选题决策/ }) })
    .first()
}

async function clickEnabledButton(locator, label) {
  await locator.waitFor({ state: 'visible', timeout: 120_000 })
  await locator.waitFor({ state: 'attached' })
  // 等轮询结束、按钮从 disabled 恢复
  for (let i = 0; i < 60; i++) {
    if (await locator.isEnabled()) break
    await locator.page().waitForTimeout(1000)
  }
  if (!(await locator.isEnabled())) {
    throw new Error(`按钮仍 disabled: ${label}`)
  }
  await locator.click()
  log(`clicked: ${label}`)
}

async function runFromContent(page, taskId) {
  await page.goto(`${FRONT}/tasks/${taskId}`)
  await contentCard(page).waitFor({ state: 'visible', timeout: 120_000 })
  log('content panel visible')

  const title = await contentCard(page).locator('.ant-card-head-title').innerText()
  log(`content card title=${title}`)
  if (!/v2/.test(title)) {
    await page.getByPlaceholder(/不满意时填写修改意见/).fill('语气更口语，多加一点 emoji')
    await clickEnabledButton(
      contentCard(page).getByRole('button', { name: '提交修改意见并重写' }),
      '提交修改意见并重写',
    )
    await contentCard(page)
      .locator('.ant-card-head-title', { hasText: /v2/ })
      .waitFor({ state: 'visible', timeout: 360_000 })
    log('content v2 ready')
  } else {
    log('already content v2, skip revise')
  }

  await clickEnabledButton(
    contentCard(page).locator('button.ant-btn-primary').filter({ hasText: /通\s*过/ }),
    '通过',
  )
  log('content approved')
}

async function runImages(page, taskId) {
  if (!page.url().includes(taskId)) {
    await page.goto(`${FRONT}/tasks/${taskId}`)
  }
  // 只认卡片标题，避免命中分步条里的「图片审核」
  await imageCard(page).waitFor({ state: 'visible', timeout: 600_000 })
  log('image panel visible')

  const alreadyRedrawn = await imageCard(page).getByText(/已重绘/).count()
  if (alreadyRedrawn === 0) {
    const secondCheck = imageCard(page).locator('.ant-checkbox-wrapper', { hasText: '第 2 张' })
    await secondCheck.click()
    await page.getByPlaceholder(/重绘要求/).fill('背景更明亮一点')
    await clickEnabledButton(
      imageCard(page).getByRole('button', { name: '重绘选中' }),
      '重绘选中',
    )
    log('redraw submitted')
    await imageCard(page).getByText(/已重绘/).first().waitFor({ state: 'visible', timeout: 360_000 })
    log('redraw done')
  } else {
    log('already redrawn, skip redraw')
  }

  await clickEnabledButton(
    imageCard(page).getByRole('button', { name: '全部通过' }),
    '全部通过',
  )
  log('images approved')
}

async function runPackage(page, taskId) {
  if (!page.url().includes('/package')) {
    await page.goto(`${FRONT}/tasks/${taskId}`)
    await waitForText(page, '查看内容包', 360_000)
    await page.getByRole('button', { name: '查看内容包' }).click()
  }
  await page.waitForURL(/\/package/, { timeout: 30_000 })
  await waitForText(page, '小红书内容包')
  log('package page OK')

  await page.getByRole('button', { name: '一键复制文字' }).click()
  log('copy button clicked')

  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 60_000 }),
    page.getByRole('button', { name: '批量下载图片' }).click(),
  ])
  const zipPath = path.join(OUT, await download.suggestedFilename())
  await download.saveAs(zipPath)
  log(`zip downloaded: ${zipPath}`)

  const markBtn = page.getByRole('button', { name: /标记已发布|已标记发布/ })
  const markText = await markBtn.innerText()
  if (markText.includes('已标记')) {
    log('already marked published')
  } else {
    await markBtn.click()
    await waitForText(page, '已标记发布', 30_000)
    log('marked published')
  }

  await page.goto(`${FRONT}/tasks`)
  await waitForText(page, '已完成')
  log('list shows completed')
}

async function main() {
  log(
    `== Stage3 frontend E2E == front=${FRONT} direction=${DIRECTION} resume=${RESUME_TASK_ID || 'none'} from=${RESUME_FROM}`,
  )

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  page.setDefaultTimeout(60_000)

  let taskId = RESUME_TASK_ID

  try {
    if (!taskId || RESUME_FROM === 'start') {
      await page.goto(`${FRONT}/tasks`)
      await waitForText(page, '任务列表')
      log('task list OK')

      await page.getByLabel('内容方向').fill(DIRECTION)
      await page.getByRole('button', { name: '创建并开始' }).click()
      await page.waitForURL(/\/tasks\/[0-9a-f-]+/, { timeout: 30_000 })
      taskId = page.url().split('/tasks/')[1]
      log(`task created: ${taskId}`)
      fs.writeFileSync(path.join(OUT, 'stage3_task_id.txt'), taskId, 'utf8')

      await topicCard(page).waitFor({ state: 'visible', timeout: 360_000 })
      log('topic panel visible')
      await page.locator('.ant-radio-wrapper').first().click()
      await clickEnabledButton(topicCard(page).getByRole('button', { name: '确认选题' }), '确认选题')
      log('topic selected')

      await runFromContent(page, taskId)
      await runImages(page, taskId)
      await runPackage(page, taskId)
    } else if (RESUME_FROM === 'topic') {
      await page.goto(`${FRONT}/tasks/${taskId}`)
      await topicCard(page).waitFor({ state: 'visible', timeout: 360_000 })
      await page.locator('.ant-radio-wrapper').first().click()
      await clickEnabledButton(topicCard(page).getByRole('button', { name: '确认选题' }), '确认选题')
      await runFromContent(page, taskId)
      await runImages(page, taskId)
      await runPackage(page, taskId)
    } else if (RESUME_FROM === 'content') {
      await runFromContent(page, taskId)
      await runImages(page, taskId)
      await runPackage(page, taskId)
    } else if (RESUME_FROM === 'images') {
      await runImages(page, taskId)
      await runPackage(page, taskId)
    } else if (RESUME_FROM === 'package') {
      await runPackage(page, taskId)
    } else {
      throw new Error(`未知 RESUME_FROM=${RESUME_FROM}`)
    }

    log('== Stage3 frontend E2E ALL PASSED ==')
  } catch (err) {
    const shot = path.join(OUT, 'stage3_e2e_fail.png')
    try {
      await page.screenshot({ path: shot, fullPage: true })
      log(`screenshot -> ${shot}`)
    } catch {
      /* ignore */
    }
    throw err
  } finally {
    fs.writeFileSync(LOG, lines.join('\n'), 'utf8')
    await browser.close()
    console.log(`log -> ${LOG}`)
  }
}

main().catch((err) => {
  console.error(err)
  try {
    fs.appendFileSync(LOG, `\n${String(err?.stack || err)}\n`, 'utf8')
  } catch {
    /* ignore */
  }
  process.exit(1)
})
