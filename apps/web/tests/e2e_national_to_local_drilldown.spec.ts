// Playwright regression specification for an authorized browser test runner.
// Current-session browser verification is recorded separately in docs/execution-status.md.
import {test,expect} from '@playwright/test';
test('national → region → province → district keeps map controls',async({page})=>{
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(process.env.HAZARD_TEST_URL??'http://127.0.0.1:3000');
  await page.getByRole('button',{name:'Northern ภาคเหนือ',exact:true}).click();
  await page.getByRole('button',{name:'Chiang Rai เชียงราย',exact:true}).click();
  await page.getByRole('button',{name:'Mae Sai แม่สาย',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Mae Sai',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'3D',exact:true}).click();
  await page.getByLabel('Metric extrusion',{exact:true}).check();
  await expect(page.getByRole('button',{name:'3D',exact:true})).toHaveAttribute('aria-pressed','true');
  await page.getByRole('button',{name:'Back to Thailand',exact:true}).click();
  await expect(page.getByText('Thailand · national view',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Basin Planned'})).toBeDisabled();
});

test('source dialog returns keyboard focus to the control that opened it',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto(process.env.HAZARD_TEST_URL??'http://127.0.0.1:3000');
  const opener=page.getByRole('button',{name:/^Source status/});
  await opener.click();
  await expect(page.getByRole('dialog',{name:'Source status'})).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(opener).toBeFocused();
  await opener.click();
  await page.getByRole('button',{name:'Close source status',exact:true}).click();
  await expect(opener).toBeFocused();
});
