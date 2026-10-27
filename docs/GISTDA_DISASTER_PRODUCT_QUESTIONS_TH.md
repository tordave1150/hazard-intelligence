# ร่างคำถามเกี่ยวกับ Disaster Platform Features

เตรียมวันที่ 27 ตุลาคม 2569 **ยังไม่ได้ส่งให้หน่วยงาน** ไม่มี key, token หรือ URL ที่มี credential

**สถานะล่าสุด:** ร่างนี้เป็นทางเลือกสำหรับขอความกระจ่าง ไม่ใช่เงื่อนไขให้หยุดงานพัฒนา โครงการกำลังทำ adapter รายวันขององครักษ์ โดยเว้นเวลาถ่ายภาพที่ไม่ทราบและไม่ใช้ metric ที่ยังไม่ยืนยันหน่วย ดู [ขอบเขตงานล่าสุด](gistda-engineering-scope-2026-10-27.md)

ผู้ดูแลที่ [บัญชีข้อมูล Disaster Platform ทางการ](https://opendata.gistda.or.th/th/dataset/flood-disaster-data) ระบุ: **disaster@gistda.or.th**

เรื่อง: ขอรายละเอียดการใช้ข้อมูล Features พื้นที่น้ำท่วมในเว็บส่วนตัวที่ไม่เชิงพาณิชย์

เรียน ผู้ดูแล GISTDA Disaster Platform

กำลังพัฒนาโครงการ Thailand Hazard Intelligence เป็นเว็บไซต์ส่วนตัวที่เปิดให้ประชาชนใช้ฟรี ไม่เชิงพาณิชย์ โดยแสดงข้อมูลพร้อมแหล่งที่มา เวลา หน่วยและข้อจำกัด และแยกข้อมูลพยากรณ์ออกจากข้อมูลดาวเทียม

ได้อ่าน [คู่มือ API](https://disaster.gistda.or.th/manual_api.pdf) และทดสอบ GET `/api/2.0/resources/features/flood/1day` ผ่าน `API-Key` header จาก backend ของโครงการแล้ว คำขอ `limit=1&offset=0&ap_idn=2604` (องครักษ์) ตอบ HTTP 200, `numberMatched=0`, `numberReturned=0`, `features=[]` เวลา API ตอบคือ 27 ตุลาคม 2569 00:03:33.525 ICT เรายังไม่ตีความว่าเป็นการยืนยันว่าไม่มีน้ำท่วม และไม่ใช้ `timeStamp` เป็นเวลาที่ดาวเทียมถ่ายภาพ

ต่อมาคำขอ 30days แบบไม่กรองอำเภอ limit=1 ตอบ HTTP 200 โดยรายงาน 184,323 รายการและคืนมา 1 รายการ เราตรวจเฉพาะชื่อ/ชนิดของ properties ทั้ง 29 ฟิลด์ ไม่ได้เผยแพร่ geometry หรือเก็บทั้ง dataset พบฟิลด์ _createdAt/_updatedAt และ _area/f_area/h3_area/rice_area แต่ยังไม่ยืนยันว่าเป็นเวลาหรือหน่วยใด จึงไม่ได้ใช้แทนเวลาถ่ายภาพหรือคำนวณพื้นที่

คำขอ STAC item รายวันจากลิงก์ catalog ทางการก็ตอบ HTTP 200 และระบุ datetime=2026-10-26T00:10:00Z (26 ต.ค. 2569 เวลา 07:10 ICT) เราเก็บความหมายเป็นเวลา nominal/search ของ item ตามมาตรฐาน STAC ยังไม่เรียกว่าเวลาถ่ายภาพของแต่ละ geometry และไม่ได้ดาวน์โหลด assets หรือใช้ footprint ของ item แทนขอบเขตน้ำท่วม ขอทราบความสัมพันธ์ระหว่างเวลาของ item, assets และแถว Features รวมถึงหน่วยของ _area/f_area/h3_area/rice_area ด้วย

ขอรายละเอียดเพื่อใช้ข้อมูลให้ถูกต้องดังนี้:

ตรวจพบเอกสาร schema ของ ArcGIS `app/GISTDA_flood/MapServer/0` และ `/1` แยกต่างหาก ทั้งคู่มี 7 ฟิลด์ เช่น `f_area`/`tam_rai` และระบุ service CRS 3857, source CRS 32647 แต่คำถามนี้มุ่งที่ **Disaster Platform `/features/flood/{window}` ซึ่ง sample มี 29 properties** รวม `h3_area`/`rice_area` ไม่ขอสมมติว่าความหมาย หน่วย CRS หรือสิทธิ์ของ ArcGIS ใช้แทน Features API ได้ ขอเอกสารที่ระบุผลิตภัณฑ์/endpoint ให้ตรงกันด้วยครับ/ค่ะ

1. **สิทธิ์เผยแพร่และ attribution:** [resource พื้นที่น้ำท่วมหนึ่งวัน](https://opendata.gistda.or.th/th/dataset/flood-disaster-data/resource/062a08da-a6a9-4db7-9af7-1d345e38563a) ระบุ License not specified ขอทราบเงื่อนไขแสดง geometry/แผนที่บนเว็บไซต์สาธารณะฟรี เก็บ snapshot ล่าสุด ประมวลผลสรุปพื้นที่ และให้ดาวน์โหลดผล พร้อมข้อความ attribution และข้อยกเว้นที่ต้องใช้
2. **เวลาและคุณภาพข้อมูล:** ขอ data dictionary และตัวอย่างที่ไม่มี credential ระบุฟิลด์ acquisition time, publication time, satellite/sensor, timezone/precision, CRS, หน่วยพื้นที่ และ quality flags รวมทั้งความหมาย/ขอบเขตของผลิตภัณฑ์ 1day, 3days, 7days และ 30days
3. **ผลลัพธ์ว่างและ coverage:** `numberMatched=0` หมายถึงไม่พบ geometry ใน dataset ณ เวลาคำขอ หรือมีสถานะ no coverage/no acquisition/data delay แยกต่างหากหรือไม่ มีข้อมูล footprint ของการสำรวจและเวลาที่สำรวจแต่ละพื้นที่หรือไม่ ตัวกรอง `ap_idn` เลือกหรือ clip geometry อย่างไร และผลที่คืนมานับซ้ำระหว่างวัน/เขตปกครองหรือไม่
4. **การเรียกใช้งาน:** ขอ quota/rate limit, limit สูงสุด, pagination ที่สอดคล้องกันระหว่างการอัปเดต dataset, ความถี่เผยแพร่และรอบ polling ที่เหมาะสม รวมถึงความหมายของ HTTP 404 เทียบกับ HTTP 200 ที่ FeatureCollection ว่าง

ระบบยังไม่เปิด layer น้ำท่วมสาธารณะจาก API นี้ และยังไม่สร้างค่าเตือนภัยหรือข้อสรุปว่าเป็นพื้นที่ปลอดภัยจากผลลัพธ์ว่าง ต้องการแสดงขอบเขตและข้อจำกัดตามความหมายที่ผู้ให้บริการกำหนด

ขอบคุณครับ/ค่ะ

---

ร่างนี้ใช้กับ Disaster Platform Features ปัจจุบัน แยกจาก [ร่างสอบถาม point route เก่า](GISTDA_PRODUCT25_SUPPORT_REQUEST_TH.md) ที่เก็บเป็นประวัติ ผู้ใช้สามารถปรับชื่อและข้อมูลติดต่อก่อนส่งเอง ไม่ต้องแนบ key, screenshot ที่มี key หรือ raw response ที่มี `links[].href` เพราะ upstream อาจสะท้อน key ในลิงก์
