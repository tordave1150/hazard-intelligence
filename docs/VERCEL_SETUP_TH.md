# ตั้งค่า Vercel สำหรับ Thailand Hazard Intelligence

โค้ดอยู่ที่ https://github.com/tordave1150/hazard-intelligence บน branch `main` แล้ว โดย CI ตรวจ Python และเว็บผ่านในการเผยแพร่ครั้งแรก

## 1. เปิดหน้าสร้างโปรเจกต์

เปิด https://vercel.com/new แล้วเลือกทีม `jedsadaporn231043-6773s-projects` ให้ถูกต้อง

การสร้างโปรเจกต์ต้องใช้สิทธิ์ Owner หรือ Member หรือ Developer ที่ได้รับสิทธิ์เสริม Create Project หากหน้าเว็บไม่อนุญาต ให้ Owner ของทีมสร้างโปรเจกต์ให้หรือเพิ่มสิทธิ์นี้ การตอบกลับ 403 จากการเชื่อมต่อของ agent ยังไม่บอกว่าบัญชีที่คุณใช้ผ่านหน้าเว็บมีสิทธิ์อะไร

คู่มือสิทธิ์และการสร้างโปรเจกต์: https://vercel.com/docs/projects/managing-projects

## 2. Import GitHub repository

เลือก Import ของ `tordave1150/hazard-intelligence` หากยังไม่เห็น repo ให้ตรวจการเชื่อมต่อ GitHub และอนุญาต Vercel GitHub App เฉพาะ repo นี้ บัญชีที่ import repository ของบัญชีบุคคลต้องเป็นเจ้าของ repo ตามเงื่อนไข Vercel

คู่มือ: https://vercel.com/docs/git/vercel-for-github

## 3. ตั้งค่าโครงสร้างโปรเจกต์

| รายการ | ค่า |
|---|---|
| Project Name | `hazard-intelligence` |
| Framework | Next.js |
| Production Branch | `main` |
| Root Directory | `apps/web` |
| Node.js | 22.x |
| Include source files outside of the Root Directory | เปิดใช้งาน |

ไฟล์ `apps/web/vercel.json` กำหนดคำสั่งไว้แล้ว:

- Install Command: `cd ../.. && npm ci`
- Build Command: `cd ../.. && npm run build`
- Output Directory: `.next`

แอปใช้ shared contracts จากนอก `apps/web` จึงต้องเปิดการรวม source นอก Root Directory หากตัวเลือกไม่แสดงในหน้า Import ให้ตรวจการตั้งค่า Root Directory ของโปรเจกต์ก่อนสั่ง deploy ใหม่

คู่มือ monorepo: https://vercel.com/docs/monorepos/monorepo-faq

## 4. ตั้งค่า MongoDB อย่างปลอดภัย

เพิ่ม environment variables ฝั่ง server ในโปรเจกต์ Vercel:

- `MONGODB_URI` — ใช้ credential ของ Atlas ที่มีสิทธิ์อ่านข้อมูลสำหรับเว็บไซต์
- `MONGODB_DB_NAME` — ชื่อฐานข้อมูลจริง

หากติดตั้ง MongoDB Atlas ผ่าน Vercel Integration ตามหน้า Connect a Project ให้เลือก Project `hazard-intelligence`, Environments `Production, Preview`, Custom Prefix `MONGODB` และเปิด Sensitive ระบบจะใช้ชื่อตัวแปร `MONGODB_URL` ตาม suffix ที่แสดงในหน้าติดตั้ง แอปรองรับทั้ง `MONGODB_URI` และ `MONGODB_URL` โดย URI มีลำดับความสำคัญก่อน ส่วนชื่อฐานข้อมูลใช้ `MONGODB_DB_NAME` หรือค่าเริ่มต้น `weather_db` หากไม่ได้ตั้งไว้

ตัวแปร URL/URI เป็นความลับและใช้เฉพาะฝั่ง server ไม่ต้องเปลี่ยนชื่อหรือคัดลอกค่าไปใส่ในแชต การตั้งค่า GitHub Actions สำหรับ ETL เป็นอีกส่วนหนึ่งและไม่ถูกคัดลอกมาจาก Integration อัตโนมัติ

การติดตั้งแบบ Native Integration จะสร้าง Atlas Organization และ Project ใหม่ที่ผูกกับทีม Vercel ผู้ติดตั้งคนแรกเป็น Organization Owner ตรวจบัญชีและ Organization จริงได้จาก Vercel → Storage → เลือก MongoDB → Open in MongoDB Atlas หากมีบัญชี Atlas เดิม ระบบอาจให้เชื่อมบัญชีเมื่อเปิดครั้งแรก จึงไม่ควรเดาว่าใช้บัญชี GitHub หรือ Google ใดจากภาพติดตั้งเพียงอย่างเดียว คู่มือทางการ: https://www.mongodb.com/docs/atlas/reference/partner-integrations/vercel/

ห้ามเติม prefix `NEXT_PUBLIC_` และไม่ต้องส่ง URI หรือรหัสผ่านในแชต

ฝั่ง GitHub ให้เพิ่มใน repository Settings → Secrets and variables → Actions:

- `MONGODB_URI` — credential สำหรับ ETL ที่เขียน latest collections ได้
- `MONGODB_DB_NAME`
- `OPEN_METEO_API_KEY` — เฉพาะกรณีใช้ commercial/customer endpoint

Secrets ของ repo เดิมไม่ได้ถูกคัดลอกอัตโนมัติ Workflow จะข้าม ingestion พร้อมแจ้งว่ายังไม่ตั้งค่า จนกว่าจะมี MongoDB secrets ครบ เว็บไซต์ที่ไม่มี snapshot จะขึ้น Unavailable และไม่สร้างค่าตัวอย่างขึ้นมาแทนข้อมูลจริง

### การตั้ง GitHub Actions secrets ครั้งแรก

1. เปิด Vercel → Storage → MongoDB → Open in MongoDB Atlas แล้วเลือก Project/Cluster ที่เชื่อมกับเว็บนี้
2. หากยังไม่มี database user สำหรับ ETL ที่ทราบรหัสผ่าน ให้สร้างผู้ใช้ใหม่ เช่น `hazard_etl` ใน Security → Database Access → Add New Database User กำหนดรหัสผ่าน และสิทธิ์ `readWrite` เฉพาะฐานข้อมูล `weather_db` ผ่าน Specific Privileges ไม่ใช้รหัสผ่านบัญชีที่ล็อกอิน Atlas
3. ในหน้า Cluster กด Connect → Drivers แล้วคัดลอก connection string สำหรับ database user ข้างต้น แทน placeholder รหัสผ่านด้วยค่าจริง และ URL-encode อักขระพิเศษของ username/password ตามคู่มือ MongoDB: https://www.mongodb.com/docs/atlas/driver-connection/
4. เปิด https://github.com/tordave1150/hazard-intelligence/settings/secrets/actions กด New repository secret เพิ่ม Name `MONGODB_URI` โดยช่อง Secret เป็น connection string ที่สมบูรณ์ ไม่ใส่เครื่องหมายคำพูด จากนั้นเพิ่มอีกตัว Name `MONGODB_DB_NAME` และ Secret `weather_db`
5. เปิด https://github.com/tordave1150/hazard-intelligence/actions เลือก Latest weather snapshot → Run workflow → branch `main` → Run workflow ระบบจะ audit ฐานข้อมูลก่อน หาก audit ไม่ผ่านจะไม่เริ่มเผยแพร่ข้อมูล
6. หลัง workflow สำเร็จ เปิด https://hazard-intelligence-lime.vercel.app/ แล้วกด Reload snapshot ข้อมูลอาจค้างใน cache ชั่วครู่ ควรเห็น snapshot ครบ 1,005 จุดพร้อมวันพยากรณ์จริง

URI และรหัสผ่านให้ป้อนตรงใน Atlas/GitHub เท่านั้น ไม่ต้องส่งให้ agent ในแชต หาก workflow มีปัญหา แจ้งชื่อขั้นตอนที่ล้มเหลวโดยไม่คัดลอก secrets

## 5. Deploy และตรวจข้อมูล

กด Deploy หลังตั้งค่าครบ แล้วเปิดหน้าโปรเจกต์และ URL ที่ได้รับ การตรวจ Atlas, การเผยแพร่ snapshot ครั้งแรก และการยืนยันว่า deployment อ่าน snapshot ได้จริงยังต้องดำเนินการต่อ

สถานะปัจจุบัน: deploy ที่ https://hazard-intelligence-lime.vercel.app/ แล้ว เว็บอ่าน MongoDB ได้แต่ยังไม่มี published snapshot ผู้ใช้กำลังตั้ง GitHub Actions secrets สำหรับ ETL ครั้งแรก

หากต้องให้ agent ตรวจและทำขั้นตอนต่อ ส่งเฉพาะ URL หน้าโปรเจกต์ Vercel หรือ URL deployment กลับมาได้ ไม่ต้องส่ง secrets

RID, TMD, HII/ThaiWater, GISTDA และ basin layers ยังมี source acceptance gates ตาม `source-acceptance.md` จึงยังไม่ถือว่าทุกส่วนของ roadmap พร้อมใช้งาน production
