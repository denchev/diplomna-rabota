import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import * as fastcsv from 'fast-csv';

const inputUrls = `1. https://dnes.dir.bg/obshtestvo/trend-za-prav-pat-ot-2009-g-pravitelstvoto-e-s-pozitiven-reyting
2. https://dnes.dir.bg/politika/naprezhenie-v-lom-iskat-ostavka-na-kmeta-sled-skandalen-zapis
3. https://dnes.dir.bg/politika/gerb-smenya-rakovodstva-na-mestni-strukturi-sled-mesets
4. https://dnes.dir.bg/temida/prokuraturata-obvini-kmeta-na-lom-za-kupuvane-na-glasove
5. https://dnes.dir.bg/politika/dps-predlaga-otpadane-na-ogranichenieto-za-izbiratelni-sektsii-izvan-es
6. https://dnes.dir.bg/politika/sledizborno-roene-vota-specheliha-pet-no-v-noviya-parlament-vlyazoha-shest-formatsii
7. https://dnes.dir.bg/politika/db-sa-protiv-razvod-s-pp-razdelenieto-e-seriozna-politicheska-greshka
8. https://dnes.dir.bg/politika/pp-predlaga-na-db-da-se-razdelyat-na-dve-grupi-v-obsht-parlamentaren-sayuz
9. https://dnes.dir.bg/politika/piarkata-na-razdora-v-gerb-vanina-koleva-ne-kadruvam-v-partiyata
10. https://dnes.dir.bg/politika/pb-obyavi-palnata-si-programa-niski-i-ploski-danatsi-i-ogranichavane-na-defitsita
11. https://dnes.dir.bg/politika/da-balgariya-i-dsb-otkazali-pokanata-na-pp-za-liderska-sreshta
12. https://dnes.dir.bg/politika/gen-reshetnikov-radev-specheli-zashtoto-balgarite-iskat-normalni-otnosheniya-s-rusiya
13. https://dnes.dir.bg/politika/pp-pravi-liderska-sreshta-db-protiv-razdyala-na-dve-pg-pishem-si-s-prodalzhavame-promyanata
14. https://dnes.dir.bg/politika/atanas-atanasov-razdelenieto-v-pp-db-e-razocharovashto-za-izbiratelite-ni-i-erozira-doverieto
15. https://dnes.dir.bg/politika/partiite-se-sporazumyaha-za-mestata-v-ns-progresivna-balgariya-shte-e-mezhdu-dps-i-vazrazhdane
16. https://dnes.dir.bg/politika/ivan-shishkov-reshenieto-za-sluzhebnite-ministri-e-iztsyalo-na-rumen-radev-1
17. https://dnes.dir.bg/politika/prodalzhavame-promyanata-svika-natsionalen-savet
18. https://dnes.dir.bg/politika/zarkov-tryabva-da-se-promeni-danachno-osiguritelnata-ni-sistema-regresivna-e
19. https://dnes.dir.bg/politika/rumen-milanov-pb-nyama-da-nasochva-balgariya-kam-rusiya-no-tryabva-uvazhenie-i-balans
20. https://dnes.dir.bg/politika/57-sa-zhenite-v-52-riya-parlament-nay-mnogo-sa-ot-pb
21. https://dnes.dir.bg/politika/nadezhda-neynski-varna-se-zhelanieto-za-glasuvane-zaradi-prozrachni-izbori
22. https://dnes.dir.bg/politika/ivan-demerdzhiev-kandev-e-podhodyasht-za-glaven-sekretar-na-mvr-pravitelstvo-tryabva-da-ima-do-sredata-na-may
23. https://dnes.dir.bg/na-fokus/tsik-obyavi-imenata-na-novite-240-deputati
24. https://dnes.dir.bg/politika/zagotovka-danni-za-izbiratelna-aktivnost-ot-2017-g-do-2026-g
25. https://dnes.dir.bg/politika/yasen-e-izborat-na-deputatite-s-dublirani-mandati-radev-izbra-sofiya-borisov-plovdiv
26. https://dnes.dir.bg/politika/asen-vasilev-vliza-ot-plovdiv-manol-peykov-ostava-izvan-parlamenta
27. https://dnes.dir.bg/politika/gerb-priemame-reshenieto-na-zhivko-todorov-kato-lichen-akt-na-otgovornost
28. https://dnes.dir.bg/politika/slavi-vasilev-uveryavam-che-shte-upravlyavame-ne-4-a-pone-8-godini
29. https://dnes.dir.bg/politika/da-balgariya-poiska-koalitsionno-sporazumenie-s-pp-i-dsb
30. https://dnes.dir.bg/politika/kmetat-na-stara-zagora-zhivko-todorov-napusna-rakovodstvoto-na-gerb
31. https://dnes.dir.bg/politika/peykov-asen-vasilev-sam-da-reshi-otkade-da-vleze-v-ns-tova-ne-e-pazarlak-mezhdu-partiite
32. https://dnes.dir.bg/politika/prenarezhdane-v-dps-19-izbrani-si-napraviha-otvod-ot-ns-piarat-na-radev-otkaza-da-e-deputat
33. https://dnes.dir.bg/politika/tsik-obyavi-mandatite-pb-sas-131-deputati-gerb-39-pp-db-37-dps-21-vazrazhdane-12
34. https://dnes.dir.bg/politika/fridrih-merts-pozdravi-rumen-radev-za-izbornata-pobeda
35. https://dnes.dir.bg/temida/sgp-za-signalite-za-kupuvane-na-glasove-golyama-chast-sa-anonimni-neyasni-i-nepotvardeni
36. https://dnes.dir.bg/politika/tsvetan-tsvetanov-za-radev-glasuvaha-ne-samo-ot-simpatiya-no-i-zaradi-otvrashtenie
37. https://dnes.dir.bg/politika/bivshiyat-pravosaden-ministar-na-gerb-otkaza-da-e-deputat-i-izliza-ot-politikata
38. https://dnes.dir.bg/temida/osadiha-na-4-mesetsa-zatvor-pri-strog-rezhim-kupuvach-na-glasove
39. https://dnes.dir.bg/politika/miroslav-ivanov-litsemerieto-na-db-e-prosto-netarpimo
40. https://dnes.dir.bg/politika/meloni-i-mitsotakis-se-obadiha-na-radev-da-go-pozdravyat-za-pobedata
41. https://dnes.dir.bg/politika/db-za-sarafov-parvoto-dzhudzhe-si-tragna-ostanalite-da-go-posledvat
42. https://dnes.dir.bg/politika/tsik-obyavyava-v-sabota-imenata-na-novite-deputati
43. https://dnes.dir.bg/politika/nikolay-popov-siyanie-sazdava-mrezha-po-mesta-nyama-da-obsluzhva-nito-radev-nito-vasilev
44. https://dnes.dir.bg/politika/valna-ot-reaktsii-ot-strana-na-db-prinudi-asen-vasilev-da-otstapi
45. https://dnes.dir.bg/politika/asen-vasilev-e-gotov-da-se-saobrazi-s-db-i-dsb-za-da-vleze-manol-peykov-v-ns
46. https://dnes.dir.bg/politika/stefka-kostadinova-ne-vliza-v-parlamenta-sled-slab-partien-i-lichen-rezultat
47. https://dnes.dir.bg/politika/shefkata-na-kabineta-na-jotova-oporkite-sreshtu-radev-v-evropeyskite-medii-se-puskat-ot-balgariya
48. https://dnes.dir.bg/politika/parvan-simeonov-balgarite-pripoznavat-radev-kato-noviya-tsentar-toy-shte-e-balansyor
49. https://dnes.dir.bg/politika/posolstvoto-na-sasht-balgarskiyat-narod-se-proiznese-i-nie-pozdravyavame-rumen-radev
50. https://dnes.dir.bg/politika/bozhanov-kritikuva-pp-db-za-razedinena-kampaniya-i-neefektivna-podredba-na-listite
51. https://dnes.dir.bg/politika/taner-ali-ako-aps-sme-zagubili-bitka-ne-sme-zagubili-voynata
52. https://dnes.dir.bg/krimi/komisar-kandev-za-pogazvaneto-na-demokratsiyata-davnost-nyama-parva-prisada-v-pleven
53. https://dnes.dir.bg/na-fokus/sled-lukanov-videnov-i-kostov-radev-e-chetvartiyat-s-absolyutno-mnozinstvo
54. https://dnes.dir.bg/politika/koi-stari-deputati-otpadat-ot-noviya-parlament
55. https://dnes.dir.bg/politika/andrey-gyurov-horata-byaha-poveche-ot-shemite-v-balgariya-mozhe-da-ima-chestni-izbori
56. https://dnes.dir.bg/sofia/zapochvat-proverki-za-nepremahnati-agitatsionni-materiali-sled-izborite-v-sofiya
57. https://dnes.dir.bg/politika/jotova-s-mnogo-visoka-otsenka-za-glavniya-sekretar-na-mvr-bih-mu-dala-shans
58. https://dnes.dir.bg/politika/nov-obshtinski-savetnik-shte-ima-v-mestniya-parlament-v-ruse
59. https://dnes.dir.bg/politika/peevski-pozdravi-rumen-radev-za-respektirashtiya-rezultat
60. https://dnes.dir.bg/politika/kostadinov-za-gerb-obratnoto-broene-zapochna-samo-kmetovete-im-gi-darzhat-oshte-nad-vodata
61. https://dnes.dir.bg/politika/borisov-kam-pp-db-dvama-se-karahme-tretiyat-specheli
62. https://dnes.dir.bg/plovdiv/vladimir-nikolov-e-parvi-po-preferentsii-v-plovdiv-izprevari-borisov-i-vasilev
63. https://dnes.dir.bg/politika/gutsanov-poiska-ostavkata-na-zarkov
64. https://dnes.dir.bg/politika/v-seloto-na-dogan-specheliha-peevski-i-radev
65. https://dnes.dir.bg/politika/otchetoha-izbori-s-nov-oblik-mashtabni-aktsii-dronove-i-sabrani-rekordni-sumi-v-broy-sreshtu-kupeniya-vot
66. https://dnes.dir.bg/politika/georgi-kandev-vsyako-deystvie-imashe-znachenie-za-chestnostta-na-vota
67. https://dnes.dir.bg/politika/osse-i-pase-kampanii-v-rabotno-vreme-razmiha-granitsata-mezhdu-darzhava-i-partiya
68. https://dnes.dir.bg/politika/progresivna-balgariya-zapochva-upravlenieto-si-s-pravosadna-reforma
69. https://dnes.dir.bg/politika/po-visokata-izbiratelna-aktivnost-ostavi-3-partii-izvan-sledvashtiya-parlament
70. https://dnes.dir.bg/politika/dps-zagubi-ludogorieto-kak-se-razpredeli-vota-po-oblasti
71. https://dnes.dir.bg/politika/slavi-trifonov-sled-tezi-izbori-si-prebroih-priyatelite
72. https://dnes.dir.bg/politika/jotova-svikva-52-roto-ns-sledvashtata-sedmitsa-ubedena-e-v-kabinet-s-parviya-mandat
73. https://dnes.dir.bg/varna/pb-pecheli-vota-vav-varna-sledvat-gerb-sds-pp-db-i-vazrazhdane
74. https://dnes.dir.bg/politika/deputatat-s-nay-dalag-stazh-jordan-tsonev-ot-dps-e-izpraven-pred-izpadane-ot-ns
75. https://dnes.dir.bg/politika/progresivna-balgariya-e-kategorichen-pobeditel-v-ruse-s-49-31
76. https://dnes.dir.bg/temida/prokuraturata-e-obvinila-za-izborni-prestapleniya-34-dushi-pri-405-arestuvani-ot-mvr
77. https://dnes.dir.bg/politika/samo-1-18-ot-mashinite-za-glasuvane-sa-dali-defekti-v-izborniya-den
78. https://dnes.dir.bg/svyat/ek-i-nato-pozdraviha-radev-s-pozhelaniya-da-raboti-za-sigurnostta-na-evropa
79. https://dnes.dir.bg/politika/pb-e-parva-sila-i-v-chuzhbina-pp-db-specheli-v-sasht-a-dps-v-turtsiya
80. https://dnes.dir.bg/politika/100-ot-protokolite-1-444-924-balgari-izbraha-radev-i-mu-dadoha-130-mandata-za-palno-mnozinstvo
81. https://dnes.dir.bg/politika/radan-kanev-nikoga-ne-e-imalo-podobna-kontsentratsiya-na-vlast-v-edin-chovek
82. https://dnes.dir.bg/svyat/kremal-privetstva-radev-predsedatelyat-na-evropeyskiya-savet-go-pozdravi-ek-ne-komentira
83. https://dnes.dir.bg/politika/pri-98-33-ot-protokolite-radev-doblizhi-letvata-ot-1-5-mln-glasa-podkrepa
84. https://dnes.dir.bg/politika/12-partii-shte-poluchavat-darzhavni-subsidii
85. https://dnes.dir.bg/politika/na-finalnata-prava-progresivna-balgariya-s-nad-1-4-mln-glasa-gerb-zapazva-vtoroto-myasto
86. https://dnes.dir.bg/politika/rumen-radev-pecheli-liderskata-bitka-v-25-mir-s-boyko-rashkov-izprevariha-boyko-borisov
87. https://dnes.dir.bg/burgas/progresivna-balgariya-pecheli-izborite-v-burgasko
88. https://dnes.dir.bg/politika/pri-96-41-protokoli-radev-kachva-do-44-7-gerb-uvelichava-avansa-pred-pp-db
89. https://dnes.dir.bg/sofia/rumen-radev-bie-v-liderskiya-25-mir-sofiya-gerb-sa-treti
90. https://dnes.dir.bg/politika/pri-91-68-ot-protokolite-gerb-izprevari-s-malko-pp-db-i-veche-sa-vtori
91. https://dnes.dir.bg/plovdiv/gerb-e-treta-politicheska-sila-v-plovdiv
92. https://dnes.dir.bg/politika/87-23-obraboteni-protokoli-radev-s-milion-i-chetvart-izbirateli-gerb-e-na-4000-glasa-zad-pp-db
93. https://dnes.dir.bg/politika/votat-v-turtsiya-peevski-pecheli-dvoyno-poveche-glasove-pred-dogan-sledva-pb
94. https://dnes.dir.bg/politika/78-24-obraboteni-protokoli-progresivna-balgariya-veche-ima-nad-1-milion-glasa
95. https://dnes.dir.bg/politika/osporvana-bitka-mezhdu-pp-db-i-gerb-za-vtoroto-myasto-pri-68-34-obraboteni-rezultati`;

// Helper to format JavaScript Date objects to "YYYY-MM-DD HH:mm:ss"
function formatToCustomString(dateObj) {
  if (!(dateObj instanceof Date) || isNaN(dateObj)) return '';
  const pad = (num) => String(num).padStart(2, '0');
  
  const year = dateObj.getFullYear();
  const month = pad(dateObj.getMonth() + 1);
  const day = pad(dateObj.getDate());
  const hours = pad(dateObj.getHours());
  const minutes = pad(dateObj.getMinutes());
  const seconds = pad(dateObj.getSeconds());
  
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

async function processAndSaveComments() {
  const waitMs = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  // Transform text strings into clean base comments URLs
  const targetUrls = inputUrls
    .split('\n')
    .map(line => line.replace(/^\d+\.\s*/, '').trim())
    .filter(url => url.length > 0)
    .map(urlStr => {
      try {
        const parsedUrl = new URL(urlStr);
        const segments = parsedUrl.pathname.split('/');
        if (segments.length >= 3) {
          segments[1] = 'comments';
          parsedUrl.pathname = segments.join('/');
        }
        return { originalUrl: urlStr, commentUrl: parsedUrl.toString() };
      } catch (err) {
        console.error(`Skipping invalid URL: ${urlStr}`);
        return null;
      }
    })
    .filter(item => item !== null);

  console.log(`Starting execution run for ${targetUrls.length} entries.\n`);

  // Setup CSV stream architectures
  const csvPath = path.join('input', 'izbori', 'dir_bg.csv');
  fs.mkdirSync(path.dirname(csvPath), { recursive: true });
  
  const writeStream = fs.createWriteStream(csvPath, { flags: 'w', encoding: 'utf8' });
  const csvStream = fastcsv.format({ headers: true });
  csvStream.pipe(writeStream);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  try {
    for (let i = 0; i < targetUrls.length; i++) {
      const { originalUrl, commentUrl } = targetUrls[i];
      console.log(`[${i + 1}/${targetUrls.length}] Loading base comment page: ${commentUrl}`);

      await page.goto(commentUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

      // Clean page title
      const pageMeta = await page.evaluate(() => {
        let rawTitle = document.querySelector('h1, .article-title')?.innerText || document.title || '';
        rawTitle = rawTitle.replace(/[\r\n]+/g, ' ');
        const cleanTitle = rawTitle
          .replace(/^Коментари\s*-\s*/gi, '')
          .replace(/\|\s*Днес\.dir\.bg/gi, '')
          .trim();
        return { title: cleanTitle };
      });

      let accumulatedComments = [];
      const maxCommentPages = 5;

      // Inner Loop: Paginate comments up to 5 pages deep
      for (let commentPageNum = 1; commentPageNum <= maxCommentPages; commentPageNum++) {
        try {
          await page.waitForSelector('.comments-wrapper', { timeout: 4000 });
        } catch (e) {
          console.log(`   -> No visible '.comments-wrapper' found on Page ${commentPageNum}. Ending pagination.`);
          break;
        }

        // Extract comments data from current page index using specified selectors
        const currentBatch = await page.evaluate(() => {
          const nodes = Array.from(
            document.querySelectorAll('.comments-wrapper .comment-block .comment')
          );

          return nodes.map((el) => {
            const blockParent = el.closest('.comment-block');
            
            // Refined target layout hierarchy definitions
            const rawAuthor = blockParent?.querySelector('.username')?.innerText || el.querySelector('.username')?.innerText || 'Anonymous';
            const rawCommentText = el.querySelector('.comment-text, .text, p')?.innerText || el.innerText;
            const rawCommentDate = el.querySelector('.time, .date, .comment-date')?.innerText || '';
            
            // Updated user vote selector mappings
            const likes = blockParent?.querySelector('.vote_up')?.innerText?.replace(/[^\d]/g, '') || el.querySelector('.vote_up')?.innerText?.replace(/[^\d]/g, '') || '0';
            const dislikes = blockParent?.querySelector('.vote_down')?.innerText?.replace(/[^\d]/g, '') || el.querySelector('.vote_down')?.innerText?.replace(/[^\d]/g, '') || '0';

            // Flat strings conversion (replace all newlines with empty string)
            const authorClean = rawAuthor.replace(/[\r\n]+/g, '').trim();
            const textClean = rawCommentText.replace(/[\r\n]+/g, '').trim();
            const dateClean = rawCommentDate.replace(/[\r\n]+/g, '').trim();

            return {
              comment: textClean,
              author: authorClean,
              comment_date: dateClean,
              likes,
              dislikes
            };
          });
        });

        accumulatedComments.push(...currentBatch);
        console.log(`   -> [Comments Page ${commentPageNum}] Collected ${currentBatch.length} comments.`);

        // Handle next pagination step if required
        if (commentPageNum < maxCommentPages) {
          const hasNextPage = await page.evaluate(() => {
            const links = Array.from(document.querySelectorAll('.main-section .pagination a'));
            const activeIndex = links.findIndex(el => el.classList.contains('active'));
            const nextPageElement = links[activeIndex + 1];

            if (nextPageElement && !nextPageElement.classList.contains('disabled')) {
              nextPageElement.click();
              return true;
            }
            return false;
          });

          if (hasNextPage) {
            // Safe execution pipeline delay wrapper for element generation rendering
            await page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 10000 }).catch(() => {});
            await page.waitForTimeout(1000);
          } else {
            break; // No more comment pages exist
          }
        }
      }

      // Compute oldest date metrics over the full multi-page batch array
      let oldestDateString = formatToCustomString(new Date()); // Fallback default
      
      if (accumulatedComments.length > 0) {
        let oldestTimestamp = Infinity;

        accumulatedComments.forEach(item => {
          if (!item.comment_date) return;
          
          const match = item.comment_date.match(/(\d{2})\.(\d{2})\.(\d{4})\s*(\d{2}):(\d{2})/) || 
                        item.comment_date.match(/(\d{2}):(\d{2})\s*(\d{2})\.(\d{2})\.(\d{4})/);
          
          if (match) {
            let day, month, year, hours, minutes;
            if (match[3].length === 4) { 
              [ , day, month, year, hours, minutes] = match;
            } else { 
              [ , hours, minutes, day, month, year] = match;
            }
            
            const parsedDate = new Date(year, month - 1, day, hours, minutes, 0);
            const ts = parsedDate.getTime();
            if (!isNaN(ts) && ts < oldestTimestamp) {
              oldestTimestamp = ts;
            }
          }
        });

        if (oldestTimestamp !== Infinity) {
          oldestDateString = formatToCustomString(new Date(oldestTimestamp));
        }
      }

      // Stream blocks onto destination file structures
      accumulatedComments.forEach((c, index) => {
        csvStream.write({
          source_site: 'dir.bg',
          category_url: 'https://dir.bg/topic/predsrochni-izbori-2026', 
          article_url: originalUrl,
          article_title: pageMeta.title,
          article_published_at: oldestDateString,
          article_views: 0,
          comment_index: index + 1,
          comment: c.comment,
          author: c.author,
          comment_date: c.comment_date,
          likes: c.likes,
          dislikes: c.dislikes,
          scraped_at: formatToCustomString(new Date())
        });
      });

      console.log(`   -> Total written for this article: ${accumulatedComments.length} rows.`);

      // Human timing throttle padding between base articles
      if (i < targetUrls.length - 1) {
        const sleepTime = Math.floor(Math.random() * (4000 - 2000 + 1)) + 2000;
        console.log(`   Waiting ${(sleepTime / 1000).toFixed(1)}s before the next base article...`);
        await waitMs(sleepTime);
      }
    }

  } catch (error) {
    console.error('An error broke the streaming pipeline:', error);
  } finally {
    csvStream.end();
    await browser.close();
    console.log(`\nExecution complete. Your data flat file is ready at: ${csvPath}`);
  }
}

processAndSaveComments();