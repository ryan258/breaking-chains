# 200 Mystery Missions for 5th Grade Detectives

Welcome to **First-Principles Forge** — a mystery-solving machine that lives on your computer. You give it a question (called a **seed**), and a whole squad of robot detectives gets to work: the **Chief** picks what to focus on, the **Clue Collector** gathers facts, the **Pattern Spotter** finds connections, the **Idea Builder** invents explanations, the **"Prove It!" Robot** tries to poke holes in everything, and the **Test Inventor** designs an experiment YOU can actually do.

The best part: you drive the whole thing by pressing single letters — **A, B, C, D, or E**. That's it. No essays. No typing marathons. Just you, a question, and five keys.

Every mission below has four parts: **Why** (why this is cool), **Idea** (your mystery), **Steps** (exactly what to type and press), and **Result** (the treasure you end up with).

**The two magic rules for every mission:**

1. **Practice mode is FREE.** When Forge asks "ready to launch?", press **D — Use deterministic preview**. That runs the whole mystery machine in practice mode: no internet, no cost, totally safe. Every mission here works in practice mode. (A teacher with a real API key can press **A** instead for live robot detectives — but you never need to.)
2. **Every mission needs only its question.** No files, no downloads, no setup. If you can type the seed, you can run the mission.

Your finished mysteries are saved as **case files** in `outputs/investigations/` — real files you can open, print, and keep forever.

---

## 1. First Missions: Learning the Machine

### 1. Wake up the mystery machine
**Why:** Every detective checks their gear before a case.
**Idea:** Make sure the machine is alive and ready.
**Steps:**
1. Type: `uv run forge config-check`
**Result:** The machine answers `Configuration OK.` — gear check complete. You didn't spend anything or touch the internet.

### 2. Solve your very first mystery
**Why:** The fastest way to learn the machine is to ride it once, start to finish.
**Idea:** A classic starter mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does my shadow change size during the day?"`
2. Press **A** for a Quick mission, then **D** for practice mode.
3. Answer every question the machine asks with one letter (the one marked "recommended" is always a safe pick).
**Result:** Your first complete case file appears in `outputs/investigations/` — facts, clues, ideas, a "Prove It!" challenge, and a real experiment you could do with a meter stick and chalk.

### 3. Read your case file like a real report
**Why:** Detectives don't just solve cases — they write them up.
**Idea:** Open your shadow mystery in fancy form.
**Steps:**
1. Type: `uv run forge list` and find your mystery's ID (it starts with `inv_`).
2. Type: `uv run forge show <that id>`
**Result:** Your case file appears in the terminal looking like a real published report, with the **Findings** (the "so what") right at the top.

### 4. See your whole case board
**Why:** Every detective show has a wall covered in cases. This is yours.
**Idea:** List every mystery you've ever run.
**Steps:**
1. Type: `uv run forge list`
**Result:** One line per case: its ID, how deep it went, what stage it reached, and the start of its question. Your case board grows every mission.

### 5. Master the five magic buttons
**Why:** The whole machine runs on A, B, C, D, E — and E is a secret door.
**Idea:** Try the custom-answer escape hatch.
**Steps:**
1. Start any mystery, and at one question press **E** instead.
2. Type a short answer in your own words when it asks.
**Result:** The machine accepts YOUR idea and keeps going. A is fast, but E means the machine never traps you in its four choices.

### 6. Prove that "no" always works
**Why:** A good machine lets you back out with nothing lost.
**Idea:** Start a mystery and then chicken out on purpose.
**Steps:**
1. Type: `uv run forge investigate --seed "Anything at all"`
2. Pick a depth, then at the launch question press **B — Stop before starting**.
**Result:** The machine says nothing was started and nothing was spent. Quitting is always allowed and always free.

### 7. Meet the robot detective squad
**Why:** Knowing who does what makes the case file make sense.
**Idea:** Spot each robot's work in a finished case.
**Steps:**
1. Type: `uv run forge show <any id>` from a finished mission.
2. Find the focus (Chief), the facts (Clue Collector), the connections (Pattern Spotter), the ideas (Idea Builder), the challenge (Prove It! Robot), and the experiment (Test Inventor).
**Result:** You can name which robot wrote each section — six specialists, one case file.

### 8. Learn the difference between a FACT and a GUESS
**Why:** This is the machine's superpower — and soon it'll be yours.
**Idea:** Hunt for both in one case file.
**Steps:**
1. Open any finished case file.
2. Find something labeled as **evidence** (a fact someone observed) and something labeled as a guess or interpretation (an idea about the fact).
**Result:** You can point at the exact line where fact ends and guessing begins. Most grown-ups can't do this. Now you can.

---

## 2. Playground & Recess Mysteries

### 9. The swing mystery
**Why:** You pump your legs and go higher — but WHY does that work?
**Idea:** Crack the physics of swinging.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does pumping my legs make the swing go higher?"`
2. Press **A**, then **D**, then answer with single letters.
**Result:** A case file that splits what you can SEE (leaning back, going higher) from ideas about WHY — plus an experiment you can run at recess.

### 10. Why do you get dizzy on the merry-go-round?
**Why:** Your body does something weird and nobody ever explains it.
**Idea:** Investigate spinning dizziness.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do I feel dizzy after spinning, and why does it keep going after I stop?"`
2. Press **A**, then **D**.
**Result:** Ideas about the spinning liquid in your ears — labeled as ideas, not facts — and a safe test: does spinning the other way un-dizzy you faster?

### 11. The four-square bounce mystery
**Why:** Some balls are bouncy monsters and some are duds.
**Idea:** What makes a ball bouncy?
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a new four-square ball bounce higher than an old squishy one?"`
2. Press **A**, then **D**.
**Result:** An experiment with a wall, a ruler, and two balls — including what result would prove the idea WRONG, which is the mark of a real experiment.

### 12. Why is the slide faster on some days?
**Why:** Same slide, same you — different speed. Suspicious.
**Idea:** Hunt the hidden variable.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does the slide feel faster on hot days than cold days?"`
2. Press **A**, then **D**.
**Result:** Suspects like clothing, temperature, and moisture get lined up, and the Test Inventor designs the fair test that catches the culprit.

### 13. The mystery of the echo
**Why:** Yelling at the gym wall talks back. Why?
**Idea:** Investigate the echo.
**Steps:**
1. Type: `uv run forge investigate --seed "Why can I hear an echo against the gym wall but not against the fence?"`
2. Press **A**, then **D**.
**Result:** A case file comparing hard walls and open fences, ending with an experiment: clap at different distances and count the delay.

### 14. Why do puddles disappear?
**Why:** Rain makes puddles; then they vanish without draining anywhere. Where did the water GO?
**Idea:** Track the missing water.
**Steps:**
1. Type: `uv run forge investigate --seed "Where does puddle water go when there is no drain?"`
2. Press **A**, then **D**.
**Result:** The evaporation idea — with a chalk experiment: outline a puddle every hour and watch the shrinking rings.

### 15. The kickball curve mystery
**Why:** Some kids can make the ball curve. Is it magic or physics?
**Idea:** Investigate the curving kick.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a kickball curve when you kick it off-center?"`
2. Press **A**, then **D**.
**Result:** Spin gets named as the prime suspect, with a fair-test experiment: kick with spin, kick without, compare paths.

### 16. Why does the seesaw work with a big kid and a little kid?
**Why:** A small kid CAN lift a big kid — if they sit in the right spot.
**Idea:** Crack the seesaw code.
**Steps:**
1. Type: `uv run forge investigate --seed "How can a smaller kid balance a bigger kid on the seesaw?"`
2. Press **A**, then **D**.
**Result:** The distance-from-the-middle idea, plus an experiment with backpacks and a ruler you can run today.

### 17. The mystery of the shady spot
**Why:** Everyone fights for the same spot under the tree at recess.
**Idea:** Why is shade cooler — really?
**Steps:**
1. Type: `uv run forge investigate --seed "Why does it feel so much cooler in the shade if the air is the same air?"`
2. Press **A**, then **D**.
**Result:** A case file separating air temperature from sunshine-on-your-skin, and a two-thermometer experiment for proof.

### 18. Why do wet shoes squeak?
**Why:** The gym floor announces you like an alarm.
**Idea:** Investigate the squeak.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do my sneakers squeak on the gym floor when they are wet?"`
2. Press **A**, then **D**.
**Result:** Grip-slip-grip ideas with a test: same shoes, wet vs. dry, same floor — and what silence would prove.

### 19. The jump-rope double-under mystery
**Why:** Two spins in one jump seems impossible. Some kids do it anyway.
**Idea:** What actually changes for a double-under?
**Steps:**
1. Type: `uv run forge investigate --seed "What has to change to do a double-under: jumping higher or spinning faster?"`
2. Press **A**, then **D**.
**Result:** Two rival ideas — jump higher vs. spin faster — and an experiment where a friend counts and times you testing each one.

### 20. Why does the flag flap?
**Why:** No hands touch it, but it never stops moving.
**Idea:** Investigate the flapping flag.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does the flag flap and snap instead of just leaning in the wind?"`
2. Press **A**, then **D**.
**Result:** The wobbling-wind idea, labeled as an idea — plus an experiment with a strip of paper and a fan at home.

---

## 3. Animal Mysteries

### 21. Why do cats purr?
**Why:** It's a motor sound coming out of a fuzzy animal. That deserves an investigation.
**Idea:** The purring case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do cats purr, and do they only purr when they are happy?"`
2. Press **A**, then **D**.
**Result:** The "only when happy" part gets flagged as an unproven guess — and the case file suggests observations that could test it.

### 22. The dog head-tilt mystery
**Why:** You talk, the dog tilts its head. Every time. Why?
**Idea:** Investigate the tilt.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do dogs tilt their heads when you talk to them?"`
2. Press **A**, then **D**.
**Result:** Hearing ideas vs. seeing ideas vs. "it gets a reaction" ideas — with an observation plan any dog owner in class can run.

### 23. How do geese know where to go?
**Why:** No maps, no phones, thousands of miles — and they make it.
**Idea:** The migration mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "How do geese find their way south without a map?"`
2. Press **A**, then **D**.
**Result:** A case file that honestly separates what the question assumes from what would need checking — the machine never pretends to know.

### 24. Why do squirrels forget their nuts?
**Why:** They bury hundreds. Do they really remember them all?
**Idea:** Investigate squirrel memory.
**Steps:**
1. Type: `uv run forge investigate --seed "Do squirrels remember where they buried their nuts or do they just search everywhere?"`
2. Press **A**, then **D**.
**Result:** Two rival explanations and — the cool part — what you'd have to observe in the schoolyard to tell them apart.

### 25. The mystery of the ant highway
**Why:** Ants march in a perfect line like they planned it in a meeting.
**Idea:** How do ants make trails?
**Steps:**
1. Type: `uv run forge investigate --seed "How do ants all follow the exact same invisible path?"`
2. Press **A**, then **D**.
**Result:** The invisible-smell-trail idea, plus a gentle experiment: rub your finger across the path (not on the ants) and watch what happens.

### 26. Why don't birds fall off branches when they sleep?
**Why:** You'd fall off. They don't. What's their trick?
**Idea:** The sleeping-grip mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "How do birds sleep standing on a branch without falling off?"`
2. Press **A**, then **D**.
**Result:** The automatic-locking-feet idea, clearly labeled as an idea to check — with what evidence would confirm it.

### 27. Can fish sleep?
**Why:** No eyelids. Always moving. So... do they?
**Idea:** Investigate fish sleep.
**Steps:**
1. Type: `uv run forge investigate --seed "Do fish sleep, and how would anyone even tell?"`
2. Press **A**, then **D**.
**Result:** The best part is the second half: the case file focuses on "how would anyone tell" — which is real science thinking.

### 28. The mystery of the purring... dog?
**Why:** Some questions test whether the machine will just make stuff up.
**Idea:** Ask something slightly off and watch the machine be careful.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do dogs purr like cats do?"`
2. Press **A**, then **D**.
**Result:** Watch closely: "dogs purr" gets treated as a claim to check, not a fact — the machine questions your question. That's a feature, not rudeness.

### 29. Why do cats always land on their feet?
**Why:** It looks like a superpower. Is it always true?
**Idea:** Investigate the "always."
**Steps:**
1. Type: `uv run forge investigate --seed "Do cats really ALWAYS land on their feet, or just usually?"`
2. Press **A**, then **D**.
**Result:** The word "always" gets challenged by the Prove It! Robot — and you learn that "usually" and "always" are totally different claims.

### 30. The earthworm rainstorm mystery
**Why:** After rain, the sidewalk is a worm party. Why do they come up?
**Idea:** Investigate worm weather.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do earthworms come onto the sidewalk when it rains?"`
2. Press **A**, then **D**.
**Result:** The drowning idea vs. the travel idea vs. the vibration idea, with an after-the-next-rain observation plan.

### 31. How do owls turn their heads so far?
**Why:** If you tried it, you'd be in trouble. Owls do it constantly.
**Idea:** The rotating-head case.
**Steps:**
1. Type: `uv run forge investigate --seed "How can owls turn their heads almost all the way around without hurting themselves?"`
2. Press **A**, then **D**.
**Result:** Extra-bones and special-blood-vessel ideas, marked with how confident the machine is and why — never just "trust me."

### 32. Why do dogs sniff EVERYTHING?
**Why:** A walk with a dog is 90% sniffing. There must be a reason.
**Idea:** Investigate the sniff.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do dogs sniff everything on a walk — what are they finding out?"`
2. Press **A**, then **D**.
**Result:** The "smell is their newspaper" idea plus an observation experiment: count sniffs at new places vs. familiar places.

---

## 4. Space & Sky Mysteries

### 33. Why doesn't the Moon fall down?
**Why:** Everything falls. The Moon doesn't. Explain THAT.
**Idea:** The greatest gravity mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "If gravity pulls everything down, why doesn't the Moon fall on us?"`
2. Press **A**, then **D**.
**Result:** The falling-but-missing idea (the Moon IS falling — and moving sideways fast enough to keep missing), built up step by step from premises.

### 34. Why is the sky blue but sunsets orange?
**Why:** Same sky, same Sun, totally different colors.
**Idea:** The two-colored sky case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why is the sky blue at noon but orange at sunset?"`
2. Press **A**, then **D**.
**Result:** The scattered-light idea with the key premise made visible: sunset light travels through MORE air. One fact, two colors.

### 35. Where do stars go in the daytime?
**Why:** They can't just leave. So where are they?
**Idea:** The vanishing stars.
**Steps:**
1. Type: `uv run forge investigate --seed "Where do the stars go during the day?"`
2. Press **A**, then **D**.
**Result:** The still-there-but-outshone idea, plus a flashlight-in-a-bright-room experiment that makes the same thing happen on your desk.

### 36. Why does the Moon change shape?
**Why:** Nothing else in the sky slowly changes shape every night.
**Idea:** The shape-shifting Moon.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does the Moon look like a different shape every few nights?"`
2. Press **A**, then **D**.
**Result:** The lamp-and-ball experiment gets designed for you: one lamp, one ball, one dark room, and you can make every Moon phase yourself.

### 37. Why can you sometimes see the Moon in the daytime?
**Why:** The Moon is supposed to be a NIGHT thing. It breaks its own rules.
**Idea:** The daytime Moon case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why can I sometimes see the Moon in the middle of the day?"`
2. Press **A**, then **D**.
**Result:** The premise "the Moon only comes out at night" gets caught and challenged — it was never true, and now you know why everyone believes it.

### 38. Do astronauts really float because there's no gravity?
**Why:** Almost everyone believes this. Almost everyone is wrong.
**Idea:** The floating astronaut trap.
**Steps:**
1. Type: `uv run forge investigate --seed "Is it true that astronauts float because there is no gravity in space?"`
2. Press **A**, then **D**.
**Result:** The Prove It! Robot attacks the "no gravity" premise — the station is FALLING around the Earth — and you get to correct adults forever.

### 39. Why do stars twinkle but planets don't?
**Why:** A secret code hiding in plain sight, every clear night.
**Idea:** The twinkle test.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do stars twinkle but planets shine steady?"`
2. Press **A**, then **D**.
**Result:** The wobbly-air idea with a real observing mission: find one twinkler and one steady light tonight and check.

### 40. How do we know how far away stars are?
**Why:** Nobody drove there with a measuring tape. So how?
**Idea:** Measuring the unmeasurable.
**Steps:**
1. Type: `uv run forge investigate --seed "How can anyone measure the distance to a star without going there?"`
2. Press **A**, then **D**.
**Result:** The wink-one-eye-then-the-other experiment (parallax) designed at desk scale: your thumb, two eyes, and a jumping background.

### 41. Why is it colder in winter if the Sun is the same Sun?
**Why:** The Sun didn't get weaker. Something else changed.
**Idea:** The winter mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "Why is winter cold if the Sun is just as big and bright as in summer?"`
2. Press **A**, then **D**.
**Result:** The tilted-Earth idea beats the farther-away idea — and a flashlight-tilted-at-paper experiment shows why slanted light is weaker light.

### 42. Could you dig a hole to the other side of the Earth?
**Why:** Every kid has planned this dig. Time to investigate it properly.
**Idea:** The ultimate tunnel.
**Steps:**
1. Type: `uv run forge investigate --seed "What would actually stop me from digging a tunnel through the Earth?"`
2. Press **A**, then **D**.
**Result:** A case file of obstacles in order (heat, pressure, melted rock), each labeled by how sure we can be — dream crushed scientifically, which is the best way.

### 43. Why doesn't the Sun burn out like a campfire?
**Why:** Fires need wood. The Sun has no wood. Yet: 4 billion years and counting.
**Idea:** The fire that isn't a fire.
**Steps:**
1. Type: `uv run forge investigate --seed "Why hasn't the Sun burned out like a campfire does?"`
2. Press **A**, then **D**.
**Result:** The premise "the Sun is a fire" gets challenged — it's not burning, it's smashing atoms — a perfect example of a wrong premise hiding inside a question.

### 44. If the universe is expanding, what is it expanding INTO?
**Why:** The question that makes even grown-ups' brains hurt.
**Idea:** Take a giant question seriously.
**Steps:**
1. Type: `uv run forge investigate --seed "What is the universe expanding into?"`
2. Press **A**, then **D**.
**Result:** Watch the machine do the honest thing: mark most of this as open questions instead of faking an answer. Knowing what you DON'T know is detective rule number one.

---

## 5. Weird Body Science

### 45. Why do we get goosebumps?
**Why:** Your skin turns into bubble wrap when you're cold OR scared. Weird.
**Idea:** The goosebump case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do I get goosebumps when I am cold and also when I hear scary music?"`
2. Press **A**, then **D**.
**Result:** The leftover-from-furry-ancestors idea, labeled with its confidence level — plus the puzzle of why ONE trick fires for TWO different feelings.

### 46. Why does your voice sound different in recordings?
**Why:** Everyone says "that's not my voice!" — but it is.
**Idea:** The two-voices mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does my recorded voice sound different from the voice I hear when I talk?"`
2. Press **A**, then **D**.
**Result:** The sound-through-your-skull idea, and a great fact-vs-guess split: everyone else has always heard recording-you.

### 47. Why do we yawn — and why is it contagious?
**Why:** You'll probably yawn just reading this. Investigate your attacker.
**Idea:** The contagious yawn.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do people yawn, and why does seeing a yawn make me yawn?"`
2. Press **A**, then **D**.
**Result:** Honest confidence labels — yawning is genuinely not fully solved — plus a countable classroom observation: does one yawn really spread?

### 48. Why do your fingers get wrinkly in the bath?
**Why:** Only fingers and toes. Never elbows. Suspicious.
**Idea:** The prune-finger case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do only my fingers and toes get wrinkly in the bath?"`
2. Press **A**, then **D**.
**Result:** The rain-tires-for-gripping idea vs. the soaking-skin idea, and a wet-marble-picking-up experiment to test the grip theory.

### 49. Why can't you tickle yourself?
**Why:** Same fingers, same ribs, zero laughs. Why?
**Idea:** The self-tickle failure.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does tickling only work when someone ELSE does it?"`
2. Press **A**, then **D**.
**Result:** The your-brain-predicts-you idea — and a surprise-yourself experiment design that's as fun to try as it sounds.

### 50. Why do you see stars when you stand up fast?
**Why:** Sparkles and dizziness out of nowhere — your body glitching.
**Idea:** The head-rush mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do I see sparkles and feel dizzy when I stand up really fast?"`
2. Press **A**, then **D**.
**Result:** The blood-is-slow-to-climb idea with a gentle test: stand up slowly vs. quickly (sitting back down if dizzy) and compare.

### 51. Why does your stomach growl?
**Why:** It growls loudest during silent reading. Always.
**Idea:** The growling stomach.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does my stomach growl, and why is it louder when I am hungry?"`
2. Press **A**, then **D**.
**Result:** The squeezing-air-and-liquid idea, and a neat premise-check: does it ONLY growl when hungry? (Track it for a day.)

### 52. Why do we have two eyes instead of one?
**Why:** One eye works fine. So why did we get issued two?
**Idea:** The two-eye advantage.
**Steps:**
1. Type: `uv run forge investigate --seed "What can two eyes do that one eye cannot?"`
2. Press **A**, then **D**.
**Result:** The depth-vision idea plus the classic experiment: cover one eye and try to touch two pencil tips together. Prepare to miss.

### 53. Why does spicy food feel HOT?
**Why:** A pepper is room temperature. Your mouth says FIRE.
**Idea:** The fake-heat case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does spicy food feel hot when it is not actually hot in temperature?"`
2. Press **A**, then **D**.
**Result:** The tricked-heat-sensor idea — spice pushes the same button real heat pushes — a perfect example of "feels like" and "is" being different facts.

### 54. Why do we forget dreams so fast?
**Why:** An entire adventure, gone before breakfast.
**Idea:** The vanishing dream.
**Steps:**
1. Type: `uv run forge investigate --seed "Why can I remember a movie for years but forget a dream in five minutes?"`
2. Press **A**, then **D**.
**Result:** Memory-saving ideas with honest confidence levels, and an experiment: keep paper by your bed and write one line the second you wake up.

### 55. Why do arms and legs "fall asleep"?
**Why:** Your own leg turns into a bag of static. Then pins and needles!
**Idea:** The sleeping limb.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does my leg fall asleep when I sit on it, and what are the pins and needles?"`
2. Press **A**, then **D**.
**Result:** The squished-nerve idea vs. the squished-blood idea — two suspects, and the case file says what evidence would separate them.

### 56. Why are yawns, sneezes, and hiccups impossible to stop?
**Why:** Your body has buttons YOU can't press or un-press.
**Idea:** The automatic body.
**Steps:**
1. Type: `uv run forge investigate --seed "Why can I control my hands but not my hiccups?"`
2. Press **A**, then **D**.
**Result:** The two-control-systems idea (the part you drive vs. the autopilot), building a real piece of body science from a silly-sounding question.

---

## 6. Food & Kitchen Science

### 57. Why does popcorn pop?
**Why:** A rock-hard kernel becomes a fluffy cloud with a BANG.
**Idea:** The exploding kernel.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does popcorn pop and why do some kernels refuse to?"`
2. Press **A**, then **D**.
**Result:** The steam-pressure idea plus a countable experiment: count the unpopped kernels in different brands (with permission to make popcorn — the best kind of homework).

### 58. Why does ice float?
**Why:** Solid things sink. Ice is solid water. Ice floats. EXPLAIN.
**Idea:** The rule-breaking ice cube.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does ice float in water when most solid things sink?"`
2. Press **A**, then **D**.
**Result:** The water-gets-bigger-when-frozen idea, and a freezer experiment: fill a container to a marked line, freeze it, check the line.

### 59. Why does soda fizz when you open it?
**Why:** Quiet bottle, then PSSSHT and a thousand bubbles from nowhere.
**Idea:** The hidden bubbles.
**Steps:**
1. Type: `uv run forge investigate --seed "Where do soda bubbles come from if the bottle looked bubble-free before I opened it?"`
2. Press **A**, then **D**.
**Result:** The gas-hiding-in-the-liquid idea with a comparison test: opened-slowly vs. opened-fast, flat-by-morning vs. capped.

### 60. Why do onions make you cry?
**Why:** A vegetable that fights back.
**Idea:** The crying-cook case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do onions make people cry, and why does it happen even across the kitchen?"`
2. Press **A**, then **D**.
**Result:** The invisible-spray idea, plus fair-test experiments people swear by (cold onion? goggles? underwater?) ranked by which would actually prove something.

### 61. Why does toast fall butter-side down?
**Why:** Everyone says it. Is it even TRUE?
**Idea:** Check the legend before explaining it.
**Steps:**
1. Type: `uv run forge investigate --seed "Does toast really land butter-side down more often, or do people just remember the bad times?"`
2. Press **A**, then **D**.
**Result:** The best lesson in the whole doc: FIRST check if the "fact" is a fact. The experiment: many drops, real tally marks, then decide.

### 62. Why does mint make your mouth feel cold?
**Why:** The opposite of the pepper mystery — fake cold!
**Idea:** The chilly trick.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does mint gum make cold water feel EXTRA cold?"`
2. Press **A**, then **D**.
**Result:** The tricked-cold-sensor idea — mint presses your "cold" button — pairing perfectly with mission 53 as the two great sensor hoaxes.

### 63. Why does bread rise?
**Why:** Dough goes in small, comes out puffy. Something inflated it.
**Idea:** The invisible baker.
**Steps:**
1. Type: `uv run forge investigate --seed "What makes bread dough puff up when nothing is added to it?"`
2. Press **A**, then **D**.
**Result:** The tiny-living-yeast idea — with a balloon-on-a-bottle experiment (yeast, sugar, warm water) that makes the invisible visible.

### 64. Why does juice taste awful after toothpaste?
**Why:** A crime scene in your own mouth, every morning.
**Idea:** The orange juice betrayal.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does orange juice taste terrible right after brushing my teeth?"`
2. Press **A**, then **D**.
**Result:** The toothpaste-turns-off-sweet-sensors idea, plus a timing experiment: how many minutes until juice tastes normal again?

### 65. Why do apples turn brown?
**Why:** Cut an apple, come back, it's rusty. Apples don't have iron... do they?
**Idea:** The browning apple.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a cut apple turn brown, and why does lemon juice stop it?"`
2. Press **A**, then **D**.
**Result:** The air-meets-apple idea with a four-slice fair test: plain, lemon juice, water, plastic wrap — one variable each, like a real lab.

### 66. Why is the middle of the microwave burrito cold?
**Why:** Lava edges, ice core. A daily injustice.
**Idea:** The uneven microwave.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does the microwave make food hot on the edges but cold in the middle?"`
2. Press **A**, then **D**.
**Result:** Hot-spot ideas plus the classic mapping experiment: a plate of shredded cheese reveals the microwave's secret hot and cold zones.

### 67. Why does shaken soda explode but stirred soda doesn't?
**Why:** Same drink, different treatment, WILDLY different results.
**Idea:** The shaken-bottle case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does shaking a soda bottle make it spray everywhere when opening it?"`
2. Press **A**, then **D**.
**Result:** The bubble-launch-pad idea, and an outdoor experiment plan with a countdown of wait-times: does patience really defuse the bottle?

### 68. Is a hot dog a sandwich? (Investigated properly.)
**Why:** The greatest lunchroom debate of all time deserves real methods.
**Idea:** Turn a food fight into premises.
**Steps:**
1. Type: `uv run forge investigate --seed "Is a hot dog a sandwich? What definition of sandwich would decide it?"`
2. Press **A**, then **D**.
**Result:** The machine shows the fight is really about DEFINITIONS, not hot dogs — pick a definition, get an answer. Argument technology.

---

## 7. Weather & Wild Nature

### 69. Where does thunder come from?
**Why:** The sky ROARS and everyone just accepts it.
**Idea:** The sound of lightning.
**Steps:**
1. Type: `uv run forge investigate --seed "What actually makes the sound of thunder?"`
2. Press **A**, then **D**.
**Result:** The lightning-heats-air-so-fast-it-booms idea, plus the count-the-seconds trick to measure a storm's distance — with the math shown.

### 70. Why is snow white when ice is clear?
**Why:** Snow IS ice. But one is see-through and one is blinding white.
**Idea:** The two faces of frozen water.
**Steps:**
1. Type: `uv run forge investigate --seed "Why is snow white if it is made of clear ice crystals?"`
2. Press **A**, then **D**.
**Result:** The light-bouncing-a-million-times idea — and a crushed-ice experiment: clear cubes become white when smashed. Same stuff, new color.

### 71. Why can you see your breath in winter?
**Why:** Winter turns everyone into a tiny dragon.
**Idea:** The visible breath.
**Steps:**
1. Type: `uv run forge investigate --seed "Why can I see my breath on cold days but not warm days?"`
2. Press **A**, then **D**.
**Result:** The tiny-cloud idea (your wet breath fogs like a mirror), plus a mirror-breathing experiment that makes a mini version indoors.

### 72. Why don't clouds fall down?
**Why:** Clouds are made of water. Water is heavy. And yet.
**Idea:** The floating lake.
**Steps:**
1. Type: `uv run forge investigate --seed "Clouds are made of water, so why don't they fall out of the sky?"`
2. Press **A**, then **D**.
**Result:** The droplets-too-tiny-to-fall-fast idea (they DO fall, incredibly slowly, while air pushes up) — a premise flip that changes the whole question.

### 73. What makes wind?
**Why:** Air just... decides to move? Who pushed it?
**Idea:** The invisible pusher.
**Steps:**
1. Type: `uv run forge investigate --seed "What makes wind start blowing — what is pushing the air?"`
2. Press **A**, then **D**.
**Result:** The warm-air-rises-cold-air-rushes-in idea, connected to a door-crack experiment with a tissue strip at the top and bottom of a doorway.

### 74. Why do leaves change color in fall?
**Why:** The trees put on a show every year. What flips the switch?
**Idea:** The autumn color case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do leaves turn red and yellow in fall — where was that color all summer?"`
2. Press **A**, then **D**.
**Result:** The colors-were-hiding-under-the-green idea, correctly labeled by confidence — plus a leaf-collecting observation plan by tree type.

### 75. Why is the ocean salty but rain isn't?
**Why:** Rain comes FROM the ocean. Where did the salt go?
**Idea:** The missing salt.
**Steps:**
1. Type: `uv run forge investigate --seed "If rain comes from the ocean, why isn't rain salty?"`
2. Press **A**, then **D**.
**Result:** The salt-stays-behind-when-water-flies idea, with a windowsill experiment: salty water in a dish, wait, taste the crust (not the dish).

### 76. Why does it get quiet when it snows?
**Why:** Snowy mornings sound... muffled. Like the world got a blanket.
**Idea:** The silent snow.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does everything sound quieter right after fresh snow?"`
2. Press **A**, then **D**.
**Result:** The fluffy-snow-swallows-sound idea — and a sharp fact-vs-guess split: is it the snow, or just fewer cars? The case file demands you check both.

### 77. Why do rainbows curve?
**Why:** Not a straight line. Not a zigzag. Always a perfect arc.
**Idea:** The bent rainbow.
**Steps:**
1. Type: `uv run forge investigate --seed "Why is a rainbow curved instead of straight?"`
2. Press **A**, then **D**.
**Result:** The every-raindrop-bends-light-at-the-same-angle idea, plus a garden-hose experiment for making your own rainbow and checking the curve.

### 78. Why does the ground steam after rain on a hot day?
**Why:** The sidewalk turns into a smoke machine.
**Idea:** The steaming street.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does the road look steamy after rain on a hot sunny day?"`
2. Press **A**, then **D**.
**Result:** Evaporation-made-visible idea, tied back to the puddle mystery (mission 14) — two cases, one culprit.

### 79. Why are deserts hot in the day but freezing at night?
**Why:** The same sand goes from oven to freezer in hours.
**Idea:** The desert temperature swing.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do deserts get super hot in the day and super cold at night?"`
2. Press **A**, then **D**.
**Result:** The no-clouds-no-blanket idea — clouds and moisture hold warmth in — explaining your own town's clear-night chills too.

### 80. Why does lightning zigzag?
**Why:** It never goes straight. Nature refuses.
**Idea:** The crooked bolt.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does lightning zigzag instead of going in a straight line?"`
2. Press **A**, then **D**.
**Result:** The path-of-least-resistance idea, honestly labeled — with the parts scientists still argue about listed as open questions.

---

## 8. How Stuff Works

### 81. How does a bike stay up?
**Why:** Standing still: you fall. Moving: you don't. What changed?
**Idea:** The impossible balance.
**Steps:**
1. Type: `uv run forge investigate --seed "Why is it easy to balance on a moving bike but impossible on a stopped one?"`
2. Press **A**, then **D**.
**Result:** Steering-into-the-fall and spinning-wheel ideas, with honest confidence — bike balance is genuinely trickier than adults think.

### 82. How does an airplane weighing tons stay in the air?
**Why:** You can't throw a rock and have it stay up. Planes are heavier than rocks.
**Idea:** The flying machine.
**Steps:**
1. Type: `uv run forge investigate --seed "How does a giant heavy airplane stay in the sky?"`
2. Press **A**, then **D**.
**Result:** Air-pushed-down-means-plane-pushed-up ideas, plus the paper-strip experiment: blow across the top of a paper strip and watch it rise.

### 83. How does a touchscreen know where your finger is?
**Why:** It ignores your sleeve but obeys your fingertip. How does it KNOW?
**Idea:** The mind-reading glass.
**Steps:**
1. Type: `uv run forge investigate --seed "How does a touchscreen tell the difference between my finger and my glove?"`
2. Press **A**, then **D**.
**Result:** The your-body-is-slightly-electric idea, plus a test list: eraser, carrot, glove, banana — predict first, then try each.

### 84. Why do boats made of metal float?
**Why:** Drop a spoon in water: sinks. A ship is a giant spoon. Floats.
**Idea:** The floating metal mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a metal ship float when a metal spoon sinks?"`
2. Press **A**, then **D**.
**Result:** The shape-holds-air idea with a foil experiment: same foil as a boat floats, crumpled into a ball sinks. Same metal, different fate.

### 85. How does a thermos know hot from cold?
**Why:** It keeps cocoa hot AND lemonade cold. Is it deciding?
**Idea:** The "smart" bottle that isn't.
**Steps:**
1. Type: `uv run forge investigate --seed "How does a thermos keep hot things hot and cold things cold — does it know which is which?"`
2. Press **A**, then **D**.
**Result:** The premise "it knows" gets demolished: it just SLOWS ALL heat travel, both directions. One rule, both jobs — a beautiful un-mystery.

### 86. Why do mirrors flip left-right but not up-down?
**Why:** A question that has started a million arguments.
**Idea:** The mirror puzzle.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a mirror swap left and right but not up and down?"`
2. Press **A**, then **D**.
**Result:** The premise itself gets challenged — mirrors actually flip front-to-back — with a write-on-clear-plastic experiment that finally makes it click.

### 87. How does soap actually clean?
**Why:** Water alone fails. Add soap: grease surrenders. What's soap's power?
**Idea:** The grease fighter.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does soapy water clean greasy hands when plain water can't?"`
2. Press **A**, then **D**.
**Result:** The one-end-grabs-water-one-end-grabs-grease idea, plus the legendary pepper-and-soap experiment: pepper flees your soapy finger.

### 88. Why does a straw look bent in water?
**Why:** Your eyes report a broken straw. Your fingers report a straight one. Someone's lying.
**Idea:** The bent-light case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a straw look broken where it enters the water?"`
2. Press **A**, then **D**.
**Result:** The light-changes-speed-in-water idea, plus the coin-in-a-cup experiment: a hidden coin appears when you pour water in. Light is the liar.

### 89. How do noise-canceling headphones DELETE sound?
**Why:** Blocking sound makes sense. ERASING it sounds like sorcery.
**Idea:** The anti-noise machine.
**Steps:**
1. Type: `uv run forge investigate --seed "How can headphones cancel noise instead of just blocking it?"`
2. Press **A**, then **D**.
**Result:** The opposite-wave idea — sound plus its mirror-twin equals silence — connected to water ripples canceling in a bathtub.

### 90. Why does a boomerang come back?
**Why:** You throw everything else away and it stays away.
**Idea:** The returning stick.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a boomerang curve back instead of flying straight like a stick?"`
2. Press **A**, then **D**.
**Result:** Spin-plus-wing ideas with confidence labels, and a safe classroom version: a cardboard cross-boomerang, flicked indoors.

### 91. How does glue know when to stick?
**Why:** Liquid in the bottle, cement on your project, and somehow not stuck inside its own bottle.
**Idea:** The picky sticker.
**Steps:**
1. Type: `uv run forge investigate --seed "Why doesn't glue stick to the inside of its own bottle?"`
2. Press **A**, then **D**.
**Result:** The needs-air-to-harden idea — the bottle keeps air out — a question that sounds silly and lands on real chemistry.

### 92. Why do wheels in movies sometimes spin backwards?
**Why:** The car goes forward. The wheels roll backward. On camera only.
**Idea:** The backwards wheel illusion.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do car wheels sometimes look like they spin backwards in videos?"`
2. Press **A**, then **D**.
**Result:** The camera-takes-snapshots idea — between frames the wheel almost finishes a turn — plus a spinning-fan-through-a-phone-camera test.

---

## 9. Sports & Games

### 93. Why does a curveball curve?
**Why:** The ball leaves the hand and then changes its mind mid-air.
**Idea:** The pitch that breaks physics (it doesn't).
**Steps:**
1. Type: `uv run forge investigate --seed "How does spin make a thrown ball curve in the air?"`
2. Press **A**, then **D**.
**Result:** The spin-drags-air idea with a beach-ball experiment — big light balls curve more, so YOU can throw a visible curve today.

### 94. Why do golf balls have dimples?
**Why:** Smooth things should fly better... right? Wrong, and that's the mystery.
**Idea:** The bumpy-ball advantage.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do golf balls have dimples instead of being smooth?"`
2. Press **A**, then **D**.
**Result:** The dimples-manage-the-air idea — a delicious case where the "obvious" premise (smooth = fast) is exactly backwards.

### 95. Is the hot hand real?
**Why:** "They're ON FIRE!" — but is a shooting streak luck or skill?
**Idea:** Investigate streaks.
**Steps:**
1. Type: `uv run forge investigate --seed "When a player makes five shots in a row, are they more likely to make the next one?"`
2. Press **A**, then **D**.
**Result:** A coin-flip comparison experiment: streaks happen in pure luck too! The case file shows how to test streaks fairly — real sports-science thinking.

### 96. Why is it harder to hit a home run in cold weather?
**Why:** Players swear the ball "dies" in April air.
**Idea:** The cold-air effect.
**Steps:**
1. Type: `uv run forge investigate --seed "Does a baseball really fly shorter in cold weather, and why would it?"`
2. Press **A**, then **D**.
**Result:** Thicker-air and stiffer-ball ideas separated, with the honest note that "players say so" is a CLAIM, not a measurement.

### 97. Why do you jump higher after swinging your arms?
**Why:** Arms up = extra height. Your arms aren't legs. So why?
**Idea:** The arm-swing boost.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does swinging my arms help me jump higher?"`
2. Press **A**, then **D**.
**Result:** A measure-it-yourself experiment: chalk on fingertips, wall, three jumps with arm swing, three without, compare the marks.

### 98. Is rock-paper-scissors really random?
**Why:** If it's pure luck, why do some kids ALWAYS win?
**Idea:** The RPS champion mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "Is rock-paper-scissors luck, or do people have patterns you can predict?"`
2. Press **A**, then **D**.
**Result:** The people-aren't-random idea plus a tally-sheet experiment: track 30 rounds and hunt for your opponent's habits.

### 99. Why does a spiral football fly farther?
**Why:** Wobbly throws die. Spirals soar. Coaches say "spiral" but never say WHY.
**Idea:** The spiral secret.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a football thrown in a spiral go farther than a wobbly throw?"`
2. Press **A**, then **D**.
**Result:** The spin-keeps-it-pointed idea (like a spinning top staying up), connected to why bullets and frisbees spin too.

### 100. Does practice REALLY make perfect?
**Why:** Adults say it constantly. Time to investigate the slogan.
**Idea:** Test the world's most repeated advice.
**Steps:**
1. Type: `uv run forge investigate --seed "Does practicing something the same way over and over always make you better at it?"`
2. Press **A**, then **D**.
**Result:** The slogan splits into testable pieces — practice WHAT, HOW, with what feedback? — and a two-week free-throw experiment with a scorecard.

### 101. Why is it so hard to rub your belly and pat your head?
**Why:** Two easy tasks become one impossible task.
**Idea:** The pat-and-rub problem.
**Steps:**
1. Type: `uv run forge investigate --seed "Why can I rub my belly and pat my head separately but not together?"`
2. Press **A**, then **D**.
**Result:** The brain-copies-one-plan-to-both-hands idea, and a practice experiment: can 5 minutes a day for a week defeat it? Track your progress.

### 102. Why do sore muscles show up TWO DAYS later?
**Why:** The stairs attack you on Wednesday for what you did on Monday.
**Idea:** The delayed ouch.
**Steps:**
1. Type: `uv run forge investigate --seed "Why are my muscles most sore two days after a big game instead of right after?"`
2. Press **A**, then **D**.
**Result:** Repair-crew ideas with honest confidence (scientists still debate this!), and a soreness diary design: rate 1–10 each morning after practice.

### 103. Is going first in tic-tac-toe an unfair advantage?
**Why:** Everyone fights to go first. Is the fight worth it?
**Idea:** Investigate first-move advantage.
**Steps:**
1. Type: `uv run forge investigate --seed "Does the player who goes first in tic-tac-toe win more often, and can the second player force a tie?"`
2. Press **A**, then **D**.
**Result:** A tournament experiment: 20 games, tally wins by who went first — plus the idea that perfect play always ties, which your data can approach.

### 104. Why does the ball bounce funny on the blacktop cracks?
**Why:** Every playground has a "dead spot" every kid knows about.
**Idea:** Map the dead spots.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a basketball bounce differently on cracks and dead spots on the playground?"`
2. Press **A**, then **D**.
**Result:** Energy-swallowed-by-the-ground ideas, and a playground-mapping experiment: drop the ball from waist height on a grid and score each bounce.

---

## 10. Silly Questions Taken Completely Seriously

### 105. Could you actually catch a cloud in a jar?
**Why:** Silly question, real science underneath.
**Idea:** Cloud-catching, investigated.
**Steps:**
1. Type: `uv run forge investigate --seed "Could I catch a piece of cloud in a jar and keep it?"`
2. Press **A**, then **D**.
**Result:** Clouds turn out to be mist that needs its exact conditions — but the case ends with a real make-a-cloud-in-a-jar experiment (warm water, ice, teacher help).

### 106. Why don't we fall off the bottom of the Earth?
**Why:** Australia exists. Australians are fine. HOW?
**Idea:** The upside-down people problem.
**Steps:**
1. Type: `uv run forge investigate --seed "Why don't people on the bottom of the Earth fall off?"`
2. Press **A**, then **D**.
**Result:** The premise "there is a bottom" gets caught red-handed — "down" means "toward the middle" everywhere. One challenged premise dissolves the whole mystery.

### 107. If you dug up a dinosaur bone, how would anyone know how old it is?
**Why:** Bones don't come with birthday cards.
**Idea:** Dating a dinosaur.
**Steps:**
1. Type: `uv run forge investigate --seed "How do scientists know a dinosaur bone is millions of years old?"`
2. Press **A**, then **D**.
**Result:** Layer-counting and atomic-clock ideas, each labeled by how they'd be checked — a serious answer that respects the silly delivery.

### 108. Why is water wet? (Or IS it?)
**Why:** The classic gotcha question, finally investigated instead of shouted.
**Idea:** Define, then decide.
**Steps:**
1. Type: `uv run forge investigate --seed "Is water itself wet, or does water only make OTHER things wet?"`
2. Press **A**, then **D**.
**Result:** Like the hot dog case, it's definitions all the way down — pick what "wet" means and the answer follows. Debate-ending technology.

### 109. Could a T-rex actually win a race against the school bus?
**Why:** Important safety information, obviously.
**Idea:** T-rex vs. bus.
**Steps:**
1. Type: `uv run forge investigate --seed "Could a T-rex outrun a school bus?"`
2. Press **A**, then **D**.
**Result:** The case file shows what's known (bone shapes, footprint spacing), what's guessed (top speed), and how confident anyone can honestly be about a race nobody can hold.

### 110. Why don't spiders get stuck in their own webs?
**Why:** They built the trap. They walk on the trap. The trap ignores them.
**Idea:** The immune spider.
**Steps:**
1. Type: `uv run forge investigate --seed "Why don't spiders get stuck in their own sticky webs?"`
2. Press **A**, then **D**.
**Result:** The not-all-threads-are-sticky idea plus careful-feet ideas — with a look-don't-touch observation plan for the next web you find.

### 111. What if everyone on Earth jumped at the same time?
**Why:** The greatest "what if" in playground history.
**Idea:** The world jump.
**Steps:**
1. Type: `uv run forge investigate --seed "What would happen if every person on Earth jumped at the exact same moment?"`
2. Press **A**, then **D**.
**Result:** Earth outweighs all of us by so much the planet barely notices — with the size-comparison premises laid out so you can re-explain it at lunch.

### 112. Why doesn't your hair hurt when it's cut?
**Why:** Cut your finger: OUCH. Cut your hair: nothing. Same you.
**Idea:** The painless haircut.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a haircut not hurt but pulling one hair does?"`
2. Press **A**, then **D**.
**Result:** The hair-is-not-alive-but-the-root-is idea — a two-part answer that explains BOTH halves of the mystery at once.

### 113. Could you really slip on a banana peel?
**Why:** Cartoons say yes. Has anyone checked?
**Idea:** Test the oldest joke in the world.
**Steps:**
1. Type: `uv run forge investigate --seed "Are banana peels actually slippery or is that just a cartoon thing?"`
2. Press **A**, then **D**.
**Result:** A friction experiment design (peel under a shoe you PUSH with your hand — nobody actually slips), turning a gag into a measurement.

### 114. Why do we say "ow" before it even hurts?
**Why:** You yell during the stumble, before the landing. Suspiciously fast.
**Idea:** The early ouch.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do people yell OW before the pain actually arrives?"`
2. Press **A**, then **D**.
**Result:** The brain-predicts-the-future idea (it saw the landing coming), connected to the can't-tickle-yourself case — same predicting brain, two mysteries.

### 115. Do fish get thirsty?
**Why:** They live IN their drink. Does that count as drinking?
**Idea:** The thirsty fish paradox.
**Steps:**
1. Type: `uv run forge investigate --seed "Do fish drink water, and can a fish be thirsty?"`
2. Press **A**, then **D**.
**Result:** A surprisingly deep answer split (saltwater fish vs. freshwater fish do OPPOSITE things), with each claim labeled by how it could be known.

### 116. Why is it impossible to lick your own elbow?
**Why:** You just tried it. Everyone tries it.
**Idea:** The forbidden lick.
**Steps:**
1. Type: `uv run forge investigate --seed "Why can almost nobody lick their own elbow?"`
2. Press **A**, then **D**.
**Result:** Arm-length-vs-neck-reach geometry as premises, plus an honest measurement plan: is "almost nobody" true? Survey the class (no licking required, just try-and-tally).

---

## 11. The Prove It! Robot Games

### 117. Feed the robot your strongest opinion
**Why:** The Prove It! Robot's whole job is finding holes — even in things you're SURE about.
**Idea:** Volunteer your favorite belief for challenge.
**Steps:**
1. Type: `uv run forge investigate --seed "Recess should be twice as long. Challenge this idea as hard as you can."`
2. Press **A**, then **D**.
**Result:** Your belief gets split into hidden assumptions ("more recess = happier AND still time to learn?") — and each one gets attacked. Survivors only.

### 118. Watch an idea get REVISED instead of rejected
**Why:** Good ideas rarely die from challenges — they get upgraded.
**Idea:** See a challenge make an idea better.
**Steps:**
1. Run any mission, then open the case file with `uv run forge show <id>`.
2. Find a challenge marked **revise** — the idea before, the objection, and the improved idea after.
**Result:** Proof that criticism is a power-up, not an insult. The upgraded idea is stronger BECAUSE it was attacked.

### 119. Find a standing objection
**Why:** When the robot's complaint can't be answered, it stays in the report forever — right next to the conclusion.
**Idea:** Hunt for an unanswered objection.
**Steps:**
1. Open a finished case file and read the **Findings** at the top.
2. Look for a standing objection sitting beside the hypotheses.
**Result:** You see a report that admits its own weak spot on page one. Ask a grown-up when they last saw a report do that.

### 120. Challenge "everybody knows"
**Why:** "Everybody knows" is where wrong facts hide.
**Idea:** Investigate a famous "fact."
**Steps:**
1. Type: `uv run forge investigate --seed "Everybody says we only use 10 percent of our brains. Is there any evidence for that?"`
2. Press **A**, then **D**.
**Result:** The famous claim gets treated as a CLAIM — the case file lists what evidence would support or destroy it, instead of just repeating it.

### 121. Challenge the goldfish memory legend
**Why:** Poor goldfish have been insulted for decades. Do they deserve it?
**Idea:** Put the three-second-memory myth on trial.
**Steps:**
1. Type: `uv run forge investigate --seed "Do goldfish really have three-second memories?"`
2. Press **A**, then **D**.
**Result:** A trainable-fish experiment design (feed at the same corner at the same time daily — do they start waiting there?) that could clear the goldfish's name.

### 122. Challenge "lightning never strikes twice"
**Why:** A saying so famous nobody checks it.
**Idea:** The twice-struck question.
**Steps:**
1. Type: `uv run forge investigate --seed "Is it true that lightning never strikes the same place twice?"`
2. Press **A**, then **D**.
**Result:** The saying collapses under one premise-check (tall buildings get hit constantly) — a two-minute case that teaches a lifetime habit: check the saying.

### 123. Challenge "carrots give you night vision"
**Why:** Someone's grandma said it. Investigate grandma. (Respectfully.)
**Idea:** The carrot claim.
**Steps:**
1. Type: `uv run forge investigate --seed "Do carrots actually improve your eyesight or is that a story?"`
2. Press **A**, then **D**.
**Result:** A split verdict — a kernel of truth (vitamins matter) wrapped in exaggeration — showing that claims aren't just TRUE or FALSE; they can be partly both.

### 124. Challenge "some kids just can't do math"
**Why:** The most dangerous claim in school, on trial at last.
**Idea:** Investigate the "math person" myth.
**Steps:**
1. Type: `uv run forge investigate --seed "Is it true that some kids just can't be good at math no matter what?"`
2. Press **A**, then **D**.
**Result:** The claim's hidden premises exposed (good HOW? by WHEN? taught HOW?) — and the case file shows what evidence the "just can't" claim would need but doesn't have.

### 125. Challenge your OWN excuse
**Why:** The bravest use of the Prove It! Robot: point it at yourself.
**Idea:** Investigate an excuse you use.
**Steps:**
1. Type: `uv run forge investigate --seed "I say I do homework better with the TV on. Challenge this."`
2. Press **A**, then **D**.
**Result:** A fair-test design: one week TV on, one week TV off, compare homework speed and mistakes. Your excuse either earns proof or retires.

### 126. Play "spot the assumption" as a class game
**Why:** Every question smuggles in assumptions. Finding them is a sport.
**Idea:** Race to predict the machine's premise list.
**Steps:**
1. Pick a seed together, like: `uv run forge investigate --seed "Why is the cafeteria pizza the most popular lunch?"`
2. BEFORE running it, everyone writes down the hidden assumptions they can spot. Then press **A**, **D**, and compare with the machine's premise list.
**Result:** Points for every assumption you caught that the machine caught too ("IS it the most popular? Measured how?"). Assumption-spotting becomes a reflex.

### 127. Ask a trick question on purpose
**Why:** See if the machine falls for a question built on a false premise.
**Idea:** The loaded question test.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do heavier things always fall faster than lighter things?"`
2. Press **A**, then **D**.
**Result:** The "always fall faster" premise gets flagged instead of swallowed — and the case points at the classic two-objects-drop experiment you can do off a chair.

### 128. Grade the machine's honesty
**Why:** The ultimate test: does it admit what it can't know?
**Idea:** Ask something unanswerable and check for fake confidence.
**Steps:**
1. Type: `uv run forge investigate --seed "What was my great-great-grandmother's favorite color?"`
2. Press **A**, then **D**.
**Result:** No evidence exists, and the case file says so — guesses stay labeled as guesses and the open questions stay open. An honesty report card, passed.

---

## 12. Science Fair Power-Ups

### 129. Turn any question into a science fair project
**Why:** The Test Inventor's job is designing the SMALLEST experiment that teaches you something — perfect science fair size.
**Idea:** Harvest a project from a mystery.
**Steps:**
1. Type: `uv run forge investigate --seed "Does the color of light change how fast a plant grows?"`
2. Press **A**, then **D**, and read the designed experiment at the end.
**Result:** A ready project: what to measure, what result you EXPECT, what result would prove you WRONG, and when to stop. That's four boxes on the judging sheet, filled.

### 130. Get the secret weapon: the "prove me wrong" prediction
**Why:** Most science fair projects only say what should happen. Judges love projects that also say what would DISPROVE them.
**Idea:** Find the disconfirming observation in any experiment.
**Steps:**
1. Open any finished case file.
2. Find the experiment's "disconfirming observation" — the result that would kill the idea.
**Result:** You can say the magic sentence to a judge: "If I had seen X, my hypothesis would have been wrong." Instant standout.

### 131. Design the paper-airplane championship experiment
**Why:** Fun to test, easy to measure, endlessly arguable — perfect.
**Idea:** Wings vs. weight.
**Steps:**
1. Type: `uv run forge investigate --seed "Does adding a paperclip to the nose make a paper airplane fly farther or crash sooner?"`
2. Press **A**, then **D**.
**Result:** A fair-test plan: same plane, same thrower, same room, ten throws with and without the clip, measure and average. Tournament rules included.

### 132. Design the memory experiment
**Why:** Test the class's brains ON the class.
**Idea:** Pictures vs. words.
**Steps:**
1. Type: `uv run forge investigate --seed "Do people remember pictures better than words?"`
2. Press **A**, then **D**.
**Result:** A two-list experiment (10 words, 10 pictures, count what's recalled), with the sneaky details handled — same time shown, mixed order, everyone tested the same way.

### 133. Design the five-second-rule experiment
**Why:** The most argued rule in every lunchroom, finally testable.
**Idea:** Does speed really matter for dropped food?
**Steps:**
1. Type: `uv run forge investigate --seed "Does picking up dropped food within five seconds actually make it cleaner than waiting?"`
2. Press **A**, then **D**.
**Result:** An experiment sized honestly for school (with the note that seeing actual germs needs a grown-up lab) — plus the humbling premise-check: what does "clean" even mean here?

### 134. Design the plant-music experiment
**Why:** Some people swear plants like music. That's a testable claim!
**Idea:** Rock vs. silence, judged by beans.
**Steps:**
1. Type: `uv run forge investigate --seed "Do plants grow differently if you play music to them every day?"`
2. Press **A**, then **D**.
**Result:** A fair-test design with the traps caught: SAME light, SAME water, SAME seeds — otherwise the music gets credit the sunny windowsill earned.

### 135. Design the handedness experiment
**Why:** Is your left hand really that much worse, or is it just out of practice?
**Idea:** Measure the gap, then attack it.
**Steps:**
1. Type: `uv run forge investigate --seed "How much worse is my non-writing hand at writing, and does one week of practice shrink the gap?"`
2. Press **A**, then **D**.
**Result:** A before/after design: time and rate a copied sentence with each hand, practice daily, re-test — your own brain as the science fair subject.

### 136. Design the taste-test experiment (with blindfolds!)
**Why:** Can people REALLY taste the difference between brands, or do labels do the tasting?
**Idea:** The blind taste test.
**Steps:**
1. Type: `uv run forge investigate --seed "Can people tell the fancy brand from the cheap brand when they cannot see the labels?"`
2. Press **A**, then **D**.
**Result:** A real blind-test protocol — hidden labels, random order, tally sheet — plus the mind-blowing premise it tests: how much of taste is actually eyesight?

### 137. Design the reaction-time experiment
**Why:** A falling-ruler catch is a stopwatch made of physics.
**Idea:** Measure your brain's speed.
**Steps:**
1. Type: `uv run forge investigate --seed "Is my reaction time faster in the morning or the afternoon?"`
2. Press **A**, then **D**.
**Result:** The dropped-ruler-catch method (catch distance = reaction speed), measured morning and afternoon for a week, averaged like a real study.

### 138. Design the "does studying with music help" experiment
**Why:** Half the class swears by it. The other half swears at it.
**Idea:** Settle it with data.
**Steps:**
1. Type: `uv run forge investigate --seed "Do students solve math problems faster with music or in silence?"`
2. Press **A**, then **D**.
**Result:** A crossover design — everyone tries BOTH conditions in different orders so practice doesn't cheat for one side. Sneaky-fair.

### 139. Learn why every experiment needs a stop rule
**Why:** "Just one more try" is how experiments (and video game nights) go wrong.
**Idea:** Find the stop condition in a designed experiment.
**Steps:**
1. Open any case file's experiment and find its stop condition (like "stop after 20 throws or one week").
**Result:** You learn the pro move: decide when to stop BEFORE you start, so you can't accidentally keep going until you get the answer you wanted.

### 140. Pre-register your prediction like a real scientist
**Why:** Writing your prediction down FIRST makes it impossible to say "I knew it all along."
**Idea:** Lock in your expected result before testing.
**Steps:**
1. Run any experiment-design mission and read the "expected observation."
2. Copy it onto paper, date it, and have a witness sign it. THEN run the real-world experiment.
**Result:** A dated, witnessed prediction — when your results come in, you compare against what you REALLY predicted, not what you remember predicting.

---

## 13. Detective Memory Tricks

### 141. Search every case you've ever solved
**Why:** A detective with 20 case files needs a way to find the right one FAST.
**Idea:** Search your whole case history in one command.
**Steps:**
1. After a few missions, type: `uv run forge search "moon"`
**Result:** Every case that mentions the moon — in its question, focus, or clues — listed with its ID, ready to reopen with `forge show`.

### 142. Search for FACTS only
**Why:** Sometimes you want only the solid stuff, no guesses mixed in.
**Idea:** Filter your search to evidence.
**Steps:**
1. Type: `uv run forge search "water" --category evidence`
**Result:** Only observed facts about water from your cases — the guesses and hunches are filtered out. Try `--category exploratory_item` to see ONLY the guesses instead.

### 143. Hunt your unproven guesses
**Why:** Every guess you never tested is a future mission waiting.
**Idea:** Build a "to-test" list from your own cases.
**Steps:**
1. Type: `uv run forge search "because" --category exploratory_item`
**Result:** A parade of your untested ideas from every case — pick the juiciest one and make it your next investigation.

### 144. Pause a mystery for recess
**Why:** Real cases don't fit in one sitting — and this machine never loses your place.
**Idea:** Stop mid-mystery and walk away.
**Steps:**
1. Start any mission and at a checkpoint choose the pause option.
2. Note the machine's promise: `Resume later with: forge resume <id>`.
**Result:** Your case freezes exactly where you stopped. Go to recess. It waits.

### 145. Resume like nothing happened
**Why:** The second half of the pause trick.
**Idea:** Pick up yesterday's case.
**Steps:**
1. Type: `uv run forge list --status paused` to see frozen cases.
2. Type: `uv run forge resume <id>` and press **A — Resume from saved work**.
**Result:** The case reopens at the exact stage you left — nothing repeated, nothing lost. Even a computer restart can't break this.

### 146. Survive a "disaster" on purpose
**Why:** What if the computer crashed mid-mystery? Let's find out safely.
**Idea:** Interrupt a case rudely and recover.
**Steps:**
1. Start a practice-mode mission, then press Ctrl-C right in the middle (the rude exit).
2. Type: `uv run forge resume <id>`
**Result:** The case picks up from its last saved step. The machine saves after every stage, so even a crash is just an unplanned pause.

### 147. Destroy the card catalog and rebuild it
**Why:** The coolest magic trick in the whole machine.
**Idea:** Delete the search index and bring it back from the dead.
**Steps:**
1. Type: `rm data/forge.sqlite3` (yes, really — it's safe).
2. Type: `uv run forge rebuild-index`
3. Type: `uv run forge search "moon"` — everything still works.
**Result:** The index rebuilds itself completely from your Markdown case files. The case files are the REAL memory; the index is just a helper that can always be regrown.

### 148. Start a sequel to a solved case
**Why:** Great mysteries spawn sequels — and the machine remembers episode one.
**Idea:** Chain a follow-up onto a finished case.
**Steps:**
1. Type: `uv run forge list` and pick a finished case's ID.
2. Type: `uv run forge investigate --seed "What should we investigate next about this?" --prior <that id>`
3. Press **A**, then **D**.
**Result:** The new case automatically carries the old case's question and focus — a real Part Two, with the connection written into the file.

### 149. Watch the Pattern Spotter connect two different cases
**Why:** The Pattern Spotter reads your OLD cases while working on new ones.
**Idea:** Give it two related mysteries and catch it cross-referencing.
**Steps:**
1. Solve the puddle mystery (mission 14), then run the steaming-road mystery (mission 78).
2. Read the new case's connections section.
**Result:** Connections to your earlier case can appear, labeled with what they're based on — your case files becoming a web instead of a pile.

### 150. Read the machine's diary of your decisions
**Why:** Every letter you pressed is saved — your choices are part of the case.
**Idea:** Audit your own A–E trail.
**Steps:**
1. Open a case file in `outputs/investigations/` with any text editor.
2. Find the recorded decisions — the depth you picked, the launch answer, every checkpoint choice.
**Result:** A complete diary of the choices YOU made. Months later, you can see exactly how you steered the case.

### 151. Print a case file for the classroom wall
**Why:** Case files are just Markdown — they go anywhere paper goes.
**Idea:** Make the case board physical.
**Steps:**
1. Open `outputs/investigations/<id>.md`, or run `uv run forge show <id>` for the pretty version.
2. Print it (or copy it into any document and print).
**Result:** A real case file on the wall — question at the top, facts, challenged ideas, and the experiment the class can actually run next.

### 152. Back up every case in one command
**Why:** Detectives protect their case files.
**Idea:** Archive your whole history.
**Steps:**
1. Type: `tar czf my-cases.tgz outputs/investigations/`
**Result:** One file containing every mystery you've ever solved — copy it to a flash drive and your entire detective career travels with you.

---

## 14. Class Debates, Settled Properly

### 153. Cats vs. dogs — with definitions first
**Why:** The oldest debate on Earth has never once defined "better."
**Idea:** Force the debate to say what it means.
**Steps:**
1. Type: `uv run forge investigate --seed "Are cats or dogs better pets — better at WHAT, for WHOM?"`
2. Press **A**, then **D**.
**Result:** The debate splits into measurable pieces (cost? training? apartment-friendly?) — and suddenly both sides can be right about different pieces. Debate upgraded.

### 154. Is summer break too long?
**Why:** A debate where kids and teachers might actually switch sides.
**Idea:** Investigate the claim behind the argument.
**Steps:**
1. Type: `uv run forge investigate --seed "Does a long summer break make kids forget what they learned?"`
2. Press **A**, then **D**.
**Result:** The "summer slide" claim gets separated into what's measured vs. assumed, with a September experiment the class could actually run (quiz yourselves on June material).

### 155. Should pets be allowed in school?
**Why:** Everyone has an opinion; nobody has listed the premises.
**Idea:** Map both sides fairly.
**Steps:**
1. Type: `uv run forge investigate --seed "What would have to be true for a classroom pet to be a good idea?"`
2. Press **A**, then **D**.
**Result:** A premise ladder — allergies, care schedules, distraction vs. motivation — where each rung is checkable. The debate becomes a checklist.

### 156. Paper books vs. screens
**Why:** Adults argue about this constantly. Bring methods.
**Idea:** Investigate reading formats.
**Steps:**
1. Type: `uv run forge investigate --seed "Do people remember stories better from paper books or from screens?"`
2. Press **A**, then **D**.
**Result:** A classroom experiment design: same story, half read on paper, half on screen, same quiz — the argument becomes a testable question with a tally sheet.

### 157. Is Monday really the worst day?
**Why:** Monday's terrible reputation has never faced a fair trial.
**Idea:** Put a whole day of the week on trial.
**Steps:**
1. Type: `uv run forge investigate --seed "Is Monday actually worse than other days or does it just have a bad reputation?"`
2. Press **A**, then **D**.
**Result:** A mood-tracking experiment: rate each day 1–10 for two weeks WITHOUT looking at what day it is until after. Reputation vs. data, head to head.

### 158. Does homework actually help?
**Why:** The debate every kid wants to win and every kid should investigate honestly.
**Idea:** Take your own side's claim seriously enough to test it.
**Steps:**
1. Type: `uv run forge investigate --seed "Does homework help kids learn more, and how would anyone measure that fairly?"`
2. Press **A**, then **D**.
**Result:** Warning: the case file may not agree with you. It splits "homework" into kinds and amounts, and the honest answer lives in the details — real investigations follow evidence, not hopes.

### 159. What's the best seat on the bus — and why do we fight for the back?
**Why:** The back seats are bumpier. We fight for them anyway. Investigate US.
**Idea:** The back-seat paradox.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do kids want the back of the bus if the ride is bumpier there?"`
2. Press **A**, then **D**.
**Result:** Physics premises (why IS it bumpier back there?) meet social premises (distance from the driver = freedom?) — one seat, two sciences.

### 160. Should the class get a longer lunch or a longer recess?
**Why:** A real choice with real trade-offs — perfect for premise-mapping.
**Idea:** Investigate the trade before voting.
**Steps:**
1. Type: `uv run forge investigate --seed "If we could add ten minutes to lunch OR recess, which helps the class more?"`
2. Press **A**, then **D**.
**Result:** "Helps more" gets defined (energy? focus? friendships?), each option's premises listed — THEN hold the class vote, with everyone arguing from the same map.

### 161. Is it better to be the oldest or youngest kid in class?
**Why:** Everyone believes their own position is the hard one.
**Idea:** Investigate birthday effects.
**Steps:**
1. Type: `uv run forge investigate --seed "Does being the oldest kid in the grade give real advantages or is that a myth?"`
2. Press **A**, then **D**.
**Result:** Claims sorted by checkability — some (sports in youth leagues) have real evidence behind them, others are pure assumption. Nuance: unlocked.

### 162. Do school uniforms change anything?
**Why:** A debate that usually runs 100% on feelings.
**Idea:** Ask what evidence would even look like.
**Steps:**
1. Type: `uv run forge investigate --seed "What would we have to measure to know if school uniforms actually change how students act?"`
2. Press **A**, then **D**.
**Result:** The debate transforms into a measurement problem — before/after comparisons, what counts as "change" — and both sides discover they've been arguing without a ruler.

### 163. Is younger-sibling life easier or harder?
**Why:** Every sibling is CERTAIN. Certainty is exactly what the machine loves to poke.
**Idea:** The sibling trial.
**Steps:**
1. Type: `uv run forge investigate --seed "Do younger siblings really have it easier, or do they just have it different?"`
2. Press **A**, then **D**.
**Result:** "Easier" decomposes into rules, hand-me-downs, attention, and expectations — with a survey experiment the class can run across its own siblings.

### 164. The great pineapple pizza ruling
**Why:** If the machine can handle this one, it can handle anything.
**Idea:** The most divisive food question, investigated with dignity.
**Steps:**
1. Type: `uv run forge investigate --seed "Is pineapple on pizza good — and is this even a question with a true answer?"`
2. Press **A**, then **D**.
**Result:** The deepest lesson in the doc, hiding under a pizza: some questions are about facts, some are about taste, and telling those apart is a superpower. (The blind taste test from mission 136 still works though.)

---

## 15. School Life & Big Kid Questions

### 165. Why is it so hard to get up for school but easy on weekends?
**Why:** Same bed, same kid, wildly different mornings.
**Idea:** The weekend miracle.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do I wake up tired on school days but early and awake on Saturdays?"`
2. Press **A**, then **D**.
**Result:** Excitement ideas vs. bedtime ideas vs. body-clock ideas — with a one-week sleep log experiment to catch the real culprit.

### 166. Why does the school day feel long but summer feels short?
**Why:** Time is supposed to tick at one speed. Your brain disagrees.
**Idea:** The rubber clock.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does a boring hour feel long while a fun day disappears?"`
2. Press **A**, then **D**.
**Result:** Attention-and-memory ideas, honestly labeled — plus a wait-and-guess experiment: estimate a minute while bored vs. while playing, and time it.

### 167. Why do I forget the answer during the test and remember it after?
**Why:** The most unfair brain glitch in school history.
**Idea:** The hallway answer.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do answers I know disappear during tests and come back the second I hand it in?"`
2. Press **A**, then **D**.
**Result:** Nervousness-blocks-memory ideas with a practice experiment: does a pretend test at home make the real one leak less?

### 168. What's the best way to memorize spelling words?
**Why:** You'll memorize hundreds of things this year — worth testing HOW.
**Idea:** Study methods, head to head.
**Steps:**
1. Type: `uv run forge investigate --seed "Is it better to study spelling words a little every day or a lot the night before?"`
2. Press **A**, then **D**.
**Result:** A self-experiment design: two matched word lists, one studied each way, tested a week later. Your own brain settles the question.

### 169. Does doodling help or hurt listening?
**Why:** Hands drawing, ears listening — helping or hurting?
**Idea:** The doodle question.
**Steps:**
1. Type: `uv run forge investigate --seed "Does doodling while listening help people remember or distract them?"`
2. Press **A**, then **D**.
**Result:** A listen-and-recall experiment (story read aloud, half the class doodling) — with the surprise that this has real science behind it worth checking against.

### 170. Why is it scary to raise your hand even when you know the answer?
**Why:** Your arm weighs nothing. Raising it weighs a ton.
**Idea:** The heavy hand.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does raising my hand feel scary even when I am sure I am right?"`
2. Press **A**, then **D**.
**Result:** What-if-I'm-wrong ideas typed as guesses about your own brain, plus a tiny brave experiment: one hand-raise a day for a week — does the fear shrink with reps?

### 171. Why do songs get stuck in your head?
**Why:** You didn't invite that song. It moved in anyway.
**Idea:** The earworm case.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do some songs get stuck in my head for days and how do I evict them?"`
2. Press **A**, then **D**.
**Result:** Loop-and-incompleteness ideas plus eviction experiments to test (sing it to the END, chew gum, replace it) — each with a tally of what worked.

### 172. Why is waiting so hard?
**Why:** Ten minutes before your turn feels longer than a whole recess.
**Idea:** Investigate patience itself.
**Steps:**
1. Type: `uv run forge investigate --seed "Why is waiting for something exciting so hard, and does anything make it easier?"`
2. Press **A**, then **D**.
**Result:** Attention ideas with a testable toolkit — distraction, counting, doing a job — ranked by which the experiment could actually measure.

### 173. Why do best friends sometimes argue MORE?
**Why:** You'd think best friends would argue least. Investigate the puzzle.
**Idea:** The best-friend argument paradox.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do I argue more with my best friend than with kids I barely know?"`
2. Press **A**, then **D**.
**Result:** More-time-together and more-honesty ideas — carefully labeled as ideas about people, plus the reminder that noticing a pattern isn't the same as knowing its cause.

### 174. Why does saying a word over and over make it sound fake?
**Why:** Say "spoon" twenty times. SPOON. It stops being a word. What?!
**Idea:** The word-melting effect.
**Steps:**
1. Type: `uv run forge investigate --seed "Why does repeating a word many times make it stop sounding like a real word?"`
2. Press **A**, then **D**.
**Result:** The tired-meaning-circuits idea (it has a real name — semantic satiation) with a timing experiment: how many repeats until the melt? Does it differ by word length?

### 175. Why does being watched make you mess up?
**Why:** You can do it perfectly — until someone's looking.
**Idea:** The audience effect.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do I mess up the thing I practiced the moment someone watches me?"`
2. Press **A**, then **D**.
**Result:** Thinking-too-hard-about-automatic-things ideas, plus a kind experiment: perform for a stuffed animal, then one friend, then three — does the effect grow with the audience?

### 176. Why is "I'm bored" a mystery worth investigating?
**Why:** Boredom shows up even with a room full of toys. Suspicious.
**Idea:** Investigate boredom itself.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do I feel bored even when I have lots of things I could do?"`
2. Press **A**, then **D**.
**Result:** Choosing-is-hard ideas vs. nothing-feels-worth-it ideas, and an experiment: does a two-item choice beat a twenty-item pile? Count how fast you start playing.

---

## 16. Time Machine & Story Mysteries

### 177. How do we know what dinosaurs looked like?
**Why:** Nobody ever saw one. The pictures look SO confident.
**Idea:** Investigate the confidence.
**Steps:**
1. Type: `uv run forge investigate --seed "How do scientists know what color and shape dinosaurs were if no one ever saw one?"`
2. Press **A**, then **D**.
**Result:** A layered answer: shapes (strong evidence — bones), skin texture (some evidence — imprints), colors (mostly guesses, some amazing exceptions). Confidence, graded honestly.

### 178. How did people know the Earth was round BEFORE spaceships?
**Why:** No photos from space, yet ancient people figured it out. How?!
**Idea:** Re-derive an ancient discovery.
**Steps:**
1. Type: `uv run forge investigate --seed "How could people prove the Earth was round two thousand years before rockets?"`
2. Press **A**, then **D**.
**Result:** Ships-sinking-over-horizons, round shadows on the Moon, different stars in different cities — each an experiment YOU could have run in ancient times. Some you still can.

### 179. How do we know what's inside the Earth if no one's been there?
**Why:** The deepest hole ever dug barely scratched the surface. Yet textbooks draw the core confidently.
**Idea:** Knowledge without visiting.
**Steps:**
1. Type: `uv run forge investigate --seed "How do scientists know the Earth has a core if nobody can dig that deep?"`
2. Press **A**, then **D**.
**Result:** The earthquake-waves-as-X-rays idea — knowledge squeezed out of indirect evidence, which is how MOST big science actually works.

### 180. Why do so many old stories have dragons?
**Why:** Cultures that never met each other all invented giant scaly monsters.
**Idea:** The universal dragon.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do stories from all over the world have dragons in them?"`
2. Press **A**, then **D**.
**Result:** Fossil-finding ideas vs. fear-mashup ideas (snake + bird + big cat), all honestly labeled as guesses — a mystery where the open questions ARE the treasure.

### 181. How does an archaeologist know how old a pot is?
**Why:** A buried pot has no receipt.
**Idea:** Dating the undateable.
**Steps:**
1. Type: `uv run forge investigate --seed "How do archaeologists figure out the age of things they dig up?"`
2. Press **A**, then **D**.
**Result:** Layer-logic (deeper = older, usually) and atomic-clock ideas, with the "usually" flagged as an assumption that floods and digging can break.

### 182. Could pirates really find treasure with a map?
**Why:** X marks the spot — but did that ever actually work?
**Idea:** Audit the pirate legend.
**Steps:**
1. Type: `uv run forge investigate --seed "Did pirates really bury treasure and make maps, or is that mostly from stories?"`
2. Press **A**, then **D**.
**Result:** The legend traced to its evidence — mostly one famous novel and very few real cases — a perfect demo of a "fact" that's really a story wearing a fact costume.

### 183. Why did people think the Sun went around the Earth?
**Why:** They weren't silly — the evidence LOOKS that way from here.
**Idea:** Respect the old mistake.
**Steps:**
1. Type: `uv run forge investigate --seed "Why did smart people believe the Sun orbits the Earth, and what evidence changed their minds?"`
2. Press **A**, then **D**.
**Result:** The best history lesson: the same observations, two explanations, and the specific evidence that broke the tie — science as a mystery solved, not facts handed down.

### 184. How do we know about the Titanic if it sank?
**Why:** The ship is at the bottom of the ocean. The movie looks like a documentary. What do we KNOW?
**Idea:** Sort the sources.
**Steps:**
1. Type: `uv run forge investigate --seed "How do we know what happened on the Titanic — what kinds of evidence exist?"`
2. Press **A**, then **D**.
**Result:** Evidence graded by kind: survivor accounts (people can misremember), the wreck itself (rusty but honest), records and telegrams (paper trail) — a source-checking masterclass on a story kids already love.

### 185. Why does every culture have a trickster story?
**Why:** Coyote, Anansi, Loki — different continents, same character. Coincidence?
**Idea:** The everywhere-trickster.
**Steps:**
1. Type: `uv run forge investigate --seed "Why do so many cultures have trickster characters in their oldest stories?"`
2. Press **A**, then **D**.
**Result:** Traveling-stories ideas vs. humans-everywhere-need-the-same-lessons ideas — unprovable in a classroom, and the case file SAYS so, which is exactly the point.

### 186. What would aliens actually need to visit us?
**Why:** Forget whether they exist — investigate the engineering.
**Idea:** The visit, taken seriously.
**Steps:**
1. Type: `uv run forge investigate --seed "What problems would aliens have to solve to actually travel to Earth?"`
2. Press **A**, then **D**.
**Result:** Distance math, fuel, time — a premise chain that turns science fiction into a physics checklist, with the genuinely unknown parts left honestly open.

### 187. How do we know Vikings reached America?
**Why:** For centuries this was "just a saga." Then someone dug in the right place.
**Idea:** A legend that got promoted to history.
**Steps:**
1. Type: `uv run forge investigate --seed "How did a Viking story become proven history — what evidence did it?"`
2. Press **A**, then **D**.
**Result:** The story-then-evidence arc: sagas (claims) → an excavated village (physical evidence) → promotion from legend to fact. Claims CAN become knowledge; here's the paperwork.

### 188. Write a mystery story using the machine's method
**Why:** Every detective story is secretly an evidence chain — now you know how to build one.
**Idea:** Use an investigation as a story skeleton.
**Steps:**
1. Type: `uv run forge investigate --seed "A classroom goldfish went missing over the weekend and the door was locked. What are the possible explanations?"`
2. Press **A**, then **D**.
**Result:** Suspect explanations with supporting clues, a challenge round that eliminates the weak ones, and a "test" that cracks the case — copy the structure, add characters, and you've got a story with a REAL mystery engine inside.

---

## 17. Grand Finale Show-Offs

### 189. Run a whole-class investigation on the big screen
**Why:** The machine also works as a webpage with five giant buttons — built for a projector.
**Idea:** The class drives one mystery together.
**Steps:**
1. Teacher types: `uv run streamlit run src/forge/ui/streamlit_app.py` and puts the browser on the projector.
2. Enter a seed the class voted for, choose Quick, and press **D** at the launch question.
3. The class votes on every A–E choice; a different kid clicks (or key-presses) each answer.
**Result:** Democracy meets detective work — thirty kids steering one investigation with five buttons, and a case file the whole class made together.

### 190. The one-letter challenge
**Why:** Prove an entire investigation can be driven with single keypresses.
**Idea:** Count every key you press after the seed.
**Steps:**
1. Run any mission and have a friend tally your keystrokes after typing the seed.
2. Answer everything with single letters (the recommended ones count!).
**Result:** A complete investigation in about a dozen keypresses. The machine was designed so someone who finds typing hard can drive everything — good design helps everyone.

### 191. The honesty race: you vs. the machine
**Why:** Who admits "I don't know" faster — kids or robots?
**Idea:** Compare confidence honesty.
**Steps:**
1. Pick a hard question (like mission 44's expanding universe). Everyone writes their answer AND how sure they are (1–10).
2. Run the mission and compare the machine's confidence labels with the class's sureness scores.
**Result:** Usually the machine claims LESS certainty than the class did — a plot twist that starts the best discussion of the year: is it smarter to sound sure or to BE careful?

### 192. Speed-run five mysteries in one sitting
**Why:** Practice mode is free and fast — so binge.
**Idea:** A mystery marathon.
**Steps:**
1. Class picks five seeds from this doc.
2. Run each with **A** (Quick) and **D** (practice), recommended letters all the way.
3. Type `uv run forge list` at the end.
**Result:** Five case files in one session and a case board that suddenly looks like a real detective's wall. `forge search` now has real material to dig through.

### 193. The premise treasure hunt
**Why:** Premises are the machine's gold. Learn to spot them at a glance.
**Idea:** Race through case files hunting premises.
**Steps:**
1. After the marathon (mission 192), split into teams, one case file each.
2. Each team lists that case's premises, then swaps files and checks each other.
**Result:** Every team can now answer the question that stumps adults: "What is this argument ASSUMING?" — the single most useful skill in this entire document.

### 194. Build the class question wall
**Why:** Open questions aren't failures — they're the to-do list of science.
**Idea:** Harvest every open question from every case.
**Steps:**
1. Go through the class's case files and copy each "open question" onto a sticky note.
2. Cover a wall section with them.
**Result:** A living wall of genuinely unanswered questions — when someone's bored (see mission 176), the wall issues the next mission.

### 195. Collect the Prove It! Robot's greatest hits
**Why:** Collect the best challenges like trading cards.
**Idea:** A hall of fame for objections.
**Steps:**
1. From the class's case files, each kid nominates the best challenge the Skeptic made.
2. Vote on the top three; read them aloud with dramatic villain voices.
**Result:** The class starts IMITATING the Skeptic in normal arguments ("okay but what's your evidence?") — which was the secret goal all along.

### 196. Predict the machine, then check
**Why:** The deepest way to learn the method is to run it in your head first.
**Idea:** Beat the machine to its own answers.
**Steps:**
1. Pick a fresh seed. Before running it, the class writes predicted premises, one guess-explanation, and an experiment idea.
2. Run the mission and score: one point per match.
**Result:** The scores climb week over week — proof the class is internalizing the method: premises first, guesses labeled, experiments smallest-possible.

### 197. The two-case connection challenge
**Why:** The Pattern Spotter finds links between cases. Can you find them first?
**Idea:** Human vs. machine pattern-spotting.
**Steps:**
1. Pick two finished cases that feel related (like the puddle and the steamy road, or the pepper and the mint).
2. Class lists connections, then run a sequel with `--prior <one of the ids>` and compare with the machine's connections section.
**Result:** Sometimes the class finds links the machine missed. Write those on the question wall — human detectives still matter.

### 198. Give the recommended letter a day off
**Why:** Find out how much the recommendations were doing.
**Idea:** Deliberately pick the NON-recommended options.
**Steps:**
1. Run a practice mission and at each checkpoint choose a reasonable option that ISN'T marked recommended.
2. Compare the case file with a recommended-letters run of the same seed.
**Result:** Different focus, different path, same honest method — the machine follows YOUR steering, and now the class knows the choices were real choices.

### 199. The teach-your-family mission
**Why:** You truly know it when you can run it at the kitchen table.
**Idea:** Take one mission home (in your head — no computer needed).
**Steps:**
1. Pick a family debate at dinner (best pizza topping, whether the dog is smart, why the WiFi is slow).
2. Run the method by hand: What are we assuming? What have we actually observed? What's a guess? What tiny test would settle it?
**Result:** The machine's method, running on pure kid-brain — which is the point of the whole thing. The computer was just training wheels.

### 200. Investigate the investigator
**Why:** The final boss: point the machine at itself.
**Idea:** The machine's own report card.
**Steps:**
1. Type: `uv run forge investigate --seed "After all these missions, does investigating questions this way actually make our class better at thinking?"`
2. Press **A**, then **D**.
**Result:** A case file about your case files: what "better at thinking" would even mean, what evidence the class actually has, an honest confidence label, and — of course — a designed experiment to find out. Mystery #201 is yours to write.
