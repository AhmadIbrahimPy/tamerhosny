/* ============================================================
   TAMER HOSNY - IMMERSIVE 3D DANCE EXPERIENCE
   ------------------------------------------------------------
   PROFESSIONAL CHOREOGRAPHY EDITION
   ------------------------------------------------------------
   • 5 visually distinct dancers - mixed cast of men and women
   • Wider formation / real depth separation
   • Smooth human-like geometry
   • Non-emissive skin + clothing
   • Balanced cinematic lighting
   • Individual choreography
   • Different movement styles, incl. a Michael Jackson style moonwalk
   • Speed variation / acceleration / deceleration
   • Synchronized group choreography
   • Featured solo spotlight segments
   • Dynamic formations
   • Grounded footwork
   • Cinematic camera parallax
   • Flying depth objects
   • Forward particles
   • Beat shockwaves
   • Lyrics synchronization
   • Mobile optimized
   • Safe inline onclick integration
   ============================================================ */

(() => {
    "use strict";

    /* ============================================================
       CONFIG
       ============================================================ */

    const CONFIG = {
        desktop: {
            dancers: 0,
            particles: 7200,
            flyingObjects: 72,
            pixelRatio: 1.35
        },

        mobile: {
            dancers: 0,
            particles: 3000,
            flyingObjects: 30,
            pixelRatio: 1.05
        },

        camera: {
            desktopZ: 24.5,
            mobileZ: 20.5,

            desktopY: 6.0,
            mobileY: 5.5,

            fov: 46,
            smoothing: 4.0
        },

        choreography: {
            individualDuration: 8.5,
            groupDuration: 6.4,
            soloDuration: 5.5,

            moveMin: 1.0,
            moveMax: 2.45,

            groupPulseSpeed: 1.0,

            poseSmoothing: 11
        },

        colors: [
            0x16cfff,
            0xff4f93,
            0x9a6bff,
            0xffc75e,
            0x5cf2a1
        ]
    };

    /* ============================================================
       SCENES
       ------------------------------------------------------------
       Distinct visual "chapters" the show cycles through - not a
       flat random mix, but a defined sequence of looks. Every
       time the camera flies through a gate ring, the show moves
       to the next scene.
       ============================================================ */

    const SCENES = [
        {
            name: "nebula",
            colors: [
                0x16cfff,
                0x5cf2a1,
                0x4fa8ff
            ],
            speedMult: 1.0,
            bloom: 0.55,
            fog: 0x060812
        },
        {
            name: "inferno",
            colors: [
                0xff4f93,
                0xffc75e,
                0xff7a3d
            ],
            speedMult: 1.22,
            bloom: 0.72,
            fog: 0x120608
        },
        {
            name: "voidwarp",
            colors: [
                0x9a6bff,
                0xd6bfff,
                0x6bd6ff
            ],
            speedMult: 1.42,
            bloom: 0.88,
            fog: 0x08061a
        }
    ];

    /* ============================================================
       GLOBAL STATE
       ============================================================ */

    let scene = null;
    let camera = null;
    let renderer = null;
    let composer = null;
    let bloomPass = null;
    let clock = null;

    let animationId = null;

    let visualizerInitialized = false;
    let visualizerVisible = false;

    /* ============================================================
       AUDIO
       ============================================================ */

    let audioContext = null;
    let analyser = null;
    let audioSource = null;
    let audioData = null;

    let bassEnergy = 0;
    let midEnergy = 0;
    let highEnergy = 0;
    let overallEnergy = 0;

    let previousBass = 0;
    let beatPulse = 0;
    let beatCooldown = 0;

    /* ============================================================
       POINTER
       ============================================================ */

    let mouseX = 0;
    let mouseY = 0;

    let smoothMouseX = 0;
    let smoothMouseY = 0;

    /* ============================================================
       DANCERS
       ============================================================ */

    let dancers = [];

    let performanceMode = "individual";

    let performanceTimer = 0;

    let individualRound = 0;
    let groupRound = 0;

    let currentFormation = 0;

    /*
     * Solo spotlight - one dancer
     * steps forward for a featured
     * showcase segment.
     */
    let soloIndex = 0;
    let soloCycles = 0;

    let lastBeatSpawnTime = -10;

    /* ============================================================
       SCENE / GATE STATE
       ============================================================ */

    let sceneMode = 0;
    let gateRing = null;
    let nextGateAt = 6.5;
    let gateFlash = 0;

    /* ============================================================
       BRAND FLASH - "Tamer Hosny" appears periodically with a
       different animation each time, holds, then fades away.
       ============================================================ */

    const BRAND_ANIMATIONS = [
        "anim-fade",
        "anim-slide",
        "anim-zoom",
        "anim-spin",
        "anim-letters",
        "anim-glitch"
    ];

    const BRAND_ANIMATION_DURATIONS = {
        "anim-fade": 3400,
        "anim-slide": 3400,
        "anim-zoom": 3200,
        "anim-spin": 3600,
        "anim-letters": 3400,
        "anim-glitch": 2900
    };

    let nextBrandAt = 5;
    let lastBrandAnimation = null;
    let brandHideTimeout = null;

    /* ============================================================
       STAGE
       ============================================================ */

    let stage = null;
    let stageLights = null;

    /* ============================================================
       DEPTH EFFECTS
       ============================================================ */

    let particleField = null;
    let particleData = null;

    let flyingObjects = [];
    let shockwaves = [];

    /* ============================================================
       LYRICS
       ============================================================ */

    let lyricsInitialized = false;
    let lyricsData = [];
    let lastLyricIndex = -1;

    /* ============================================================
       CHOREOGRAPHY
       ============================================================ */

    const INDIVIDUAL_MOVES = [
        "groove",
        "slide",
        "shoulderWave",
        "bodyRoll",
        "footSwitch",
        "shuffle",
        "power",
        "isolation",
        "turn",
        "pose",
        "moonwalk"
    ];

    const GROUP_MOVES = [
        "bounce",
        "arms",
        "step",
        "wave",
        "power",
        "pose",
        "hit"
    ];

    const FORMATIONS = [
        "line",
        "v",
        "arc",
        "wide",
        "center"
    ];

    const PERSONALITIES = [
        "hero",
        "groover",
        "smooth",
        "power",
        "wild"
    ];

    /* ============================================================
       DOM
       ============================================================ */

    const container =
        document.getElementById(
            "audioVisualizerContainer"
        );

    const canvas =
        document.getElementById(
            "visualizerCanvas"
        );

    const toggleButton =
        document.getElementById(
            "visualizerToggleBtn"
        );

    const lyricsElement =
        document.getElementById(
            "visualizerLyricsText"
        );

    const brandElement =
        document.getElementById(
            "visualizerBrandText"
        );

    const progressTrack =
        document.getElementById(
            "visualizerProgress"
        );

    const progressFill =
        document.getElementById(
            "visualizerProgressFill"
        );

    const progressCurrentEl =
        document.getElementById(
            "visualizerCurrentTime"
        );

    const progressDurationEl =
        document.getElementById(
            "visualizerDuration"
        );

    if (!container || !canvas) {
        console.warn(
            "[Visualizer] Required DOM elements not found."
        );

        return;
    }

    /* ============================================================
       HELPERS
       ============================================================ */

    function isMobile() {
        return window.innerWidth <= 768;
    }

    function clamp(
        value,
        min,
        max
    ) {
        return Math.max(
            min,
            Math.min(
                max,
                value
            )
        );
    }

    function lerp(
        a,
        b,
        t
    ) {
        return (
            a +
            (b - a) *
            t
        );
    }

    function damp(
        current,
        target,
        lambda,
        delta
    ) {
        if (
            typeof THREE ===
                "undefined" ||
            !THREE.MathUtils
        ) {
            return lerp(
                current,
                target,
                clamp(
                    lambda *
                        delta,
                    0,
                    1
                )
            );
        }

        return THREE.MathUtils.damp(
            current,
            target,
            lambda,
            delta
        );
    }

    function dampAngle(
        current,
        target,
        lambda,
        delta
    ) {
        let diff =
            THREE.MathUtils.euclideanModulo(
                target -
                    current +
                    Math.PI,
                Math.PI * 2
            ) -
            Math.PI;

        return (
            current +
            diff *
                (
                    1 -
                    Math.exp(
                        -lambda *
                        delta
                    )
                )
        );
    }

    function random(
        min,
        max
    ) {
        return (
            min +
            Math.random() *
                (max - min)
        );
    }

    function randomChoice(
        array
    ) {
        return array[
            Math.floor(
                Math.random() *
                    array.length
            )
        ];
    }

    function smoothStep(
        t
    ) {
        t =
            clamp(
                t,
                0,
                1
            );

        return (
            t *
            t *
            (3 - 2 * t)
        );
    }

    function easeInOut(
        t
    ) {
        t =
            clamp(
                t,
                0,
                1
            );

        return t < 0.5
            ? 2 * t * t
            : 1 -
                  Math.pow(
                      -2 * t + 2,
                      2
                  ) /
                      2;
    }

    /*
     * Smooth acceleration curve.
     *
     * Starts slow -> fast -> slows.
     */
    function motionCurve(
        t
    ) {
        return (
            0.5 -
            0.5 *
                Math.cos(
                    t *
                        Math.PI *
                        2
                )
        );
    }

    /* ============================================================
       AUDIO
       ============================================================ */

    function initAudio() {
        if (
            !window.globalAudio
        ) {
            console.warn(
                "[Visualizer] globalAudio not found."
            );

            return false;
        }

        try {
            if (!audioContext) {
                audioContext =
                    new (
                        window.AudioContext ||
                        window.webkitAudioContext
                    )();
            }

            if (
                audioContext.state ===
                "suspended"
            ) {
                audioContext
                    .resume()
                    .catch(
                        () => {}
                    );
            }

            if (!analyser) {
                analyser =
                    audioContext.createAnalyser();

                analyser.fftSize =
                    512;

                analyser.smoothingTimeConstant =
                    0.72;

                audioData =
                    new Uint8Array(
                        analyser.frequencyBinCount
                    );
            }

            if (!audioSource) {
                try {
                    audioSource =
                        audioContext.createMediaElementSource(
                            window.globalAudio
                        );

                    audioSource.connect(
                        analyser
                    );

                    analyser.connect(
                        audioContext.destination
                    );

                } catch (error) {
                    /*
                     * MediaElementSource may already
                     * exist for the same audio element.
                     */
                    console.warn(
                        "[Visualizer] Audio source already connected."
                    );
                }
            }

            return true;

        } catch (error) {
            console.error(
                "[Visualizer] Audio initialization failed:",
                error
            );

            return false;
        }
    }

    function getBand(
        startRatio,
        endRatio
    ) {
        if (
            !audioData ||
            !audioData.length
        ) {
            return 0;
        }

        const start =
            Math.floor(
                audioData.length *
                    startRatio
            );

        const end =
            Math.max(
                start + 1,
                Math.floor(
                    audioData.length *
                        endRatio
                )
            );

        let total = 0;

        for (
            let i = start;
            i < end;
            i++
        ) {
            total +=
                audioData[i];
        }

        return clamp(
            (
                total /
                (end - start)
            ) / 255,
            0,
            1
        );
    }

    function updateAudio(
        delta
    ) {
        if (
            !analyser ||
            !audioData
        ) {
            bassEnergy *=
                0.95;

            midEnergy *=
                0.95;

            highEnergy *=
                0.95;

            overallEnergy *=
                0.95;

            beatPulse *=
                0.88;

            return;
        }

        analyser.getByteFrequencyData(
            audioData
        );

        const bass =
            getBand(
                0.00,
                0.085
            );

        const mid =
            getBand(
                0.085,
                0.38
            );

        const high =
            getBand(
                0.38,
                0.88
            );

        bassEnergy =
            lerp(
                bassEnergy,
                bass,
                0.28
            );

        midEnergy =
            lerp(
                midEnergy,
                mid,
                0.20
            );

        highEnergy =
            lerp(
                highEnergy,
                high,
                0.18
            );

        overallEnergy =
            lerp(
                overallEnergy,
                bass * 0.52 +
                    mid * 0.33 +
                    high * 0.15,
                0.20
            );

        const deltaBass =
            bassEnergy -
            previousBass;

        if (
            deltaBass > 0.052 &&
            bassEnergy > 0.27 &&
            beatCooldown <= 0
        ) {
            beatPulse =
                1;

            beatCooldown =
                0.15;
        }

        previousBass =
            bassEnergy;

        beatCooldown -=
            delta;

        if (
            beatCooldown < 0
        ) {
            beatCooldown = 0;
        }

        beatPulse *=
            Math.pow(
                0.025,
                delta
            );
    }

    function getVisualizerAverageFrequency() {
        if (
            !audioData ||
            !audioData.length
        ) {
            return 0;
        }

        let total = 0;

        for (
            let i = 0;
            i <
            audioData.length;
            i++
        ) {
            total +=
                audioData[i];
        }

        return (
            total /
            audioData.length
        );
    }

    /* ============================================================
       MATERIALS
       ============================================================ */

    /*
     * Skin:
     * No emissive.
     * No metallic look.
     * Soft realistic response.
     */
    function createSkinMaterial(
        variation
    ) {
        const palette = [
            0x9b6656,
            0xa9715d,
            0x8f5d4f,
            0xb27a65,
            0x965f50
        ];

        const material =
            new THREE.MeshStandardMaterial({
                color:
                    palette[
                        variation %
                            palette.length
                    ],

                roughness: 0.82,

                metalness: 0.0,

                emissive:
                    0x000000,

                emissiveIntensity:
                    0
            });

        return material;
    }

    function createBodyMaterial() {
        const material =
            new THREE.MeshStandardMaterial({
                color: 0x242a34,

                roughness: 0.70,

                metalness: 0.10,

                emissive:
                    0x000000,

                emissiveIntensity:
                    0
            });

        return material;
    }

    function createClothMaterial(
        index
    ) {
        /*
         * Distinct clothing colors,
         * but intentionally dark enough
         * that highlights remain visible.
         */
        const palette = [
            0x263142,
            0x30303d,
            0x292f3c,
            0x35302b,
            0x263831
        ];

        return new THREE.MeshStandardMaterial({
            color:
                palette[
                    index %
                        palette.length
                ],

            roughness: 0.78,

            metalness: 0.02,

            emissive:
                0x000000,

            emissiveIntensity:
                0
        });
    }

    /*
     * Only tiny costume details glow.
     */
    function createAccentMaterial(
        color
    ) {
        return new THREE.MeshStandardMaterial({
            color,

            roughness: 0.42,

            metalness: 0.25,

            emissive:
                color,

            emissiveIntensity:
                0.08
        });
    }

    /* ============================================================
       SMOOTH GEOMETRY
       ============================================================ */

    function finalizeMesh(
        mesh
    ) {
        if (
            mesh.geometry
        ) {
            mesh.geometry.computeVertexNormals();
        }

        return mesh;
    }

    function createLimb(
        length,
        radius,
        material
    ) {
        const pivot =
            new THREE.Group();

        let geometry;

        /*
         * CapsuleGeometry gives much softer
         * human-looking limbs.
         */
        if (
            typeof THREE.CapsuleGeometry !==
            "undefined"
        ) {
            geometry =
                new THREE.CapsuleGeometry(
                    radius,
                    Math.max(
                        0.05,
                        length -
                            radius * 2
                    ),
                    5,
                    10
                );
        } else {
            geometry =
                new THREE.CylinderGeometry(
                    radius,
                    radius *
                        0.92,
                    length,
                    24,
                    3,
                    false
                );
        }

        const mesh =
            new THREE.Mesh(
                geometry,
                material
            );

        mesh.position.y =
            -length /
            2;

        finalizeMesh(
            mesh
        );

        pivot.add(
            mesh
        );

        return pivot;
    }

    function createJoint(
        radius,
        material
    ) {
        const mesh =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    radius,
                    16,
                    12
                ),
                material
            );

        return finalizeMesh(
            mesh
        );
    }

    function createTorso(
        material
    ) {
        /*
         * A lathed profile gives a real
         * human torso silhouette - narrow
         * waist, wider chest, tapering to
         * the neck - instead of a straight
         * barrel shape.
         */
        const profile = [
            [0.66, -1.20],
            [0.60, -0.85],
            [0.58, -0.40],
            [0.66, 0.00],
            [0.80, 0.45],
            [0.74, 0.85],
            [0.55, 1.10],
            [0.32, 1.20]
        ].map(
            ([
                radius,
                y
            ]) =>
                new THREE.Vector2(
                    radius,
                    y
                )
        );

        const geometry =
            new THREE.LatheGeometry(
                profile,
                20
            );

        const mesh =
            new THREE.Mesh(
                geometry,
                material
            );

        mesh.scale.z =
            0.64;

        return finalizeMesh(
            mesh
        );
    }

    /* ============================================================
       POSE
       ============================================================ */

    function createPose() {
        return {
            rootX: 0,
            rootZ: 0,
            rootYRot: 0,

            torsoX: 0,
            torsoY: 0,
            torsoZ: 0,

            chestX: 0,
            chestY: 0,
            chestZ: 0,

            headX: 0,
            headY: 0,
            headZ: 0,

            shoulderLX: 0,
            shoulderLY: 0,
            shoulderLZ: 0,

            shoulderRX: 0,
            shoulderRY: 0,
            shoulderRZ: 0,

            upperArmLX: 0,
            upperArmLY: 0,
            upperArmLZ: 0,

            upperArmRX: 0,
            upperArmRY: 0,
            upperArmRZ: 0,

            forearmLX: 0,
            forearmLY: 0,
            forearmLZ: 0,

            forearmRX: 0,
            forearmRY: 0,
            forearmRZ: 0,

            hipLX: 0,
            hipLY: 0,
            hipLZ: 0,

            hipRX: 0,
            hipRY: 0,
            hipRZ: 0,

            thighLX: 0,
            thighLY: 0,
            thighLZ: 0,

            thighRX: 0,
            thighRY: 0,
            thighRZ: 0,

            shinLX: 0,
            shinLY: 0,
            shinLZ: 0,

            shinRX: 0,
            shinRY: 0,
            shinRZ: 0,

            footLX: 0,
            footLY: 0,
            footLZ: 0,

            footRX: 0,
            footRY: 0,
            footRZ: 0
        };
    }

    function resetPose(
        target
    ) {
        Object.assign(
            target,
            createPose()
        );
    }

    function applyPose(
        rig,
        target,
        delta
    ) {
        const lambda =
            CONFIG.choreography
                .poseSmoothing;

        /*
         * Never move root Y.
         */
        rig.root.position.x =
            damp(
                rig.root.position.x,
                target.rootX,
                lambda,
                delta
            );

        rig.root.position.y =
            0;

        rig.root.position.z =
            damp(
                rig.root.position.z,
                target.rootZ,
                lambda,
                delta
            );

        rig.root.rotation.y =
            dampAngle(
                rig.root.rotation.y,
                target.rootYRot,
                lambda,
                delta
            );

        function rotate(
            object,
            x,
            y,
            z
        ) {
            object.rotation.x =
                damp(
                    object.rotation.x,
                    x,
                    lambda,
                    delta
                );

            object.rotation.y =
                damp(
                    object.rotation.y,
                    y,
                    lambda,
                    delta
                );

            object.rotation.z =
                damp(
                    object.rotation.z,
                    z,
                    lambda,
                    delta
                );
        }

        rotate(
            rig.torso,
            target.torsoX,
            target.torsoY,
            target.torsoZ
        );

        rotate(
            rig.chest,
            target.chestX,
            target.chestY,
            target.chestZ
        );

        rotate(
            rig.head,
            target.headX,
            target.headY,
            target.headZ
        );

        rotate(
            rig.shoulderL,
            target.shoulderLX,
            target.shoulderLY,
            target.shoulderLZ
        );

        rotate(
            rig.shoulderR,
            target.shoulderRX,
            target.shoulderRY,
            target.shoulderRZ
        );

        rotate(
            rig.upperArmL,
            target.upperArmLX,
            target.upperArmLY,
            target.upperArmLZ
        );

        rotate(
            rig.upperArmR,
            target.upperArmRX,
            target.upperArmRY,
            target.upperArmRZ
        );

        rotate(
            rig.forearmL,
            target.forearmLX,
            target.forearmLY,
            target.forearmLZ
        );

        rotate(
            rig.forearmR,
            target.forearmRX,
            target.forearmRY,
            target.forearmRZ
        );

        rotate(
            rig.hipL,
            target.hipLX,
            target.hipLY,
            target.hipLZ
        );

        rotate(
            rig.hipR,
            target.hipRX,
            target.hipRY,
            target.hipRZ
        );

        rotate(
            rig.thighL,
            target.thighLX,
            target.thighLY,
            target.thighLZ
        );

        rotate(
            rig.thighR,
            target.thighRX,
            target.thighRY,
            target.thighRZ
        );

        rotate(
            rig.shinL,
            target.shinLX,
            target.shinLY,
            target.shinLZ
        );

        rotate(
            rig.shinR,
            target.shinRX,
            target.shinRY,
            target.shinRZ
        );

        rotate(
            rig.footL,
            target.footLX,
            target.footLY,
            target.footLZ
        );

        rotate(
            rig.footR,
            target.footRX,
            target.footRY,
            target.footRZ
        );
    }

    /* ============================================================
       DANCER CREATION
       ============================================================ */

    function createDancer(
        index,
        accentColor
    ) {
        const root =
            new THREE.Group();

        root.userData.index =
            index;

        root.userData.personality =
            PERSONALITIES[
                index %
                    PERSONALITIES.length
            ];

        root.userData.phase =
            index *
                0.61 +
            random(
                -0.20,
                0.20
            );

        root.userData.mirror =
            index % 2 === 0
                ? 1
                : -1;

        /*
         * Different body proportions.
         */
        const proportionSet = [
            {
                scale: 1.00,
                shoulder: 1.00,
                torso: 1.00,
                leg: 1.00
            },
            {
                scale: 0.92,
                shoulder: 0.94,
                torso: 0.94,
                leg: 1.05
            },
            {
                scale: 0.98,
                shoulder: 1.05,
                torso: 1.02,
                leg: 0.98
            },
            {
                scale: 0.88,
                shoulder: 0.93,
                torso: 0.91,
                leg: 1.05
            },
            {
                scale: 0.96,
                shoulder: 1.02,
                torso: 0.96,
                leg: 1.02
            }
        ];

        /*
         * Alternating male / female cast -
         * a mixed group of men and women.
         */
        root.userData.gender =
            index % 2 === 0
                ? "male"
                : "female";

        const baseProportions =
            proportionSet[
                index %
                    proportionSet.length
            ];

        const genderShape =
            root.userData.gender ===
            "female"
                ? {
                      shoulder: 0.90,
                      hip: 1.24
                  }
                : {
                      shoulder: 1.08,
                      hip: 0.90
                  };

        root.userData.proportions = {
            scale:
                baseProportions.scale,

            shoulder:
                baseProportions.shoulder *
                genderShape.shoulder,

            torso:
                baseProportions.torso,

            leg:
                baseProportions.leg,

            hip:
                genderShape.hip
        };

        const bodyMaterial =
            createBodyMaterial();

        const clothMaterial =
            createClothMaterial(
                index
            );

        const skinMaterial =
            createSkinMaterial(
                index
            );

        const accentMaterial =
            createAccentMaterial(
                accentColor
            );

        const rig = {
            root,

            pelvis:
                new THREE.Group(),

            torso:
                new THREE.Group(),

            chest:
                new THREE.Group(),

            neck:
                new THREE.Group(),

            head:
                new THREE.Group(),

            shoulderL:
                new THREE.Group(),

            shoulderR:
                new THREE.Group(),

            upperArmL:
                null,

            upperArmR:
                null,

            elbowL:
                new THREE.Group(),

            elbowR:
                new THREE.Group(),

            forearmL:
                null,

            forearmR:
                null,

            handL:
                new THREE.Group(),

            handR:
                new THREE.Group(),

            hipL:
                new THREE.Group(),

            hipR:
                new THREE.Group(),

            thighL:
                null,

            thighR:
                null,

            kneeL:
                new THREE.Group(),

            kneeR:
                new THREE.Group(),

            shinL:
                null,

            shinR:
                null,

            footL:
                new THREE.Group(),

            footR:
                new THREE.Group(),

            target:
                createPose()
        };

        root.userData.rig =
            rig;

        /* ========================================================
           PELVIS
           ======================================================== */

        const proportions =
            root.userData.proportions;

        rig.pelvis.position.y =
            5.80 *
            proportions.leg;

        root.add(
            rig.pelvis
        );

        const pelvisMesh =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    0.86,
                    18,
                    14
                ),
                clothMaterial
            );

        pelvisMesh.scale.set(
            1.02 *
                proportions.hip,
            0.58,
            0.70 *
                proportions.hip
        );

        rig.pelvis.add(
            pelvisMesh
        );

        /* ========================================================
           TORSO
           ======================================================== */

        rig.torso.position.y =
            0.34;

        rig.torso.scale.y =
            proportions.torso;

        rig.pelvis.add(
            rig.torso
        );

        const torsoMesh =
            createTorso(
                bodyMaterial
            );

        torsoMesh.scale.x *=
            0.98;

        rig.torso.add(
            torsoMesh
        );

        /* ========================================================
           CHEST
           ======================================================== */

        rig.chest.position.y =
            1.18;

        rig.torso.add(
            rig.chest
        );

        rig.chest.scale.x =
            proportions.shoulder;

        /*
         * A rounded shell instead of a flat
         * box - it follows the body's curve
         * like an open shirt front rather
         * than looking like an armor plate.
         */
        const chestPanel =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    0.74,
                    18,
                    14
                ),
                clothMaterial
            );

        chestPanel.position.z =
            0.14;

        chestPanel.scale.set(
            0.92,
            0.80,
            0.34
        );

        finalizeMesh(
            chestPanel
        );

        rig.chest.add(
            chestPanel
        );

        /* ========================================================
           NECK
           ======================================================== */

        rig.neck.position.y =
            0.98;

        rig.chest.add(
            rig.neck
        );

        const neckMesh =
            new THREE.Mesh(
                new THREE.CylinderGeometry(
                    0.225,
                    0.28,
                    0.50,
                    14
                ),
                skinMaterial
            );

        finalizeMesh(
            neckMesh
        );

        rig.neck.add(
            neckMesh
        );

        /* ========================================================
           HEAD
           ======================================================== */

        rig.head.position.y =
            0.73;

        rig.neck.add(
            rig.head
        );

        const headMesh =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    0.56,
                    20,
                    16
                ),
                skinMaterial
            );

        headMesh.scale.set(
            0.88,
            1.04,
            0.93
        );

        finalizeMesh(
            headMesh
        );

        rig.head.add(
            headMesh
        );

        /* ========================================================
           HAIR
           ======================================================== */

        const hair =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    0.59,
                    18,
                    12,
                    0,
                    Math.PI * 2,
                    0,
                    Math.PI *
                        0.49
                ),
                bodyMaterial
            );

        hair.position.y =
            0.16;

        finalizeMesh(
            hair
        );

        rig.head.add(
            hair
        );

        /*
         * Female dancers get a tied-back
         * ponytail; reads clearly at a
         * distance and swings with movement.
         */
        if (
            root.userData.gender ===
            "female"
        ) {
            const ponytail =
                new THREE.Mesh(
                    new THREE.ConeGeometry(
                        0.16,
                        0.85,
                        10
                    ),
                    bodyMaterial
                );

            ponytail.rotation.x =
                Math.PI *
                0.62;

            ponytail.position.set(
                0,
                0.10,
                -0.52
            );

            finalizeMesh(
                ponytail
            );

            rig.head.add(
                ponytail
            );
        }

        /*
         * The "hero" personality is the
         * Michael Jackson tribute dancer -
         * a tilted fedora and a single
         * sequined glove.
         */
        if (
            root.userData.personality ===
            "hero"
        ) {
            const hat =
                new THREE.Group();

            const brim =
                new THREE.Mesh(
                    new THREE.CylinderGeometry(
                        0.62,
                        0.62,
                        0.05,
                        20
                    ),
                    bodyMaterial
                );

            const crown =
                new THREE.Mesh(
                    new THREE.CylinderGeometry(
                        0.40,
                        0.44,
                        0.42,
                        20
                    ),
                    bodyMaterial
                );

            crown.position.y =
                0.22;

            finalizeMesh(
                brim
            );

            finalizeMesh(
                crown
            );

            hat.add(
                brim
            );

            hat.add(
                crown
            );

            hat.position.set(
                0,
                0.42,
                0.06
            );

            hat.rotation.z =
                0.18;

            rig.head.add(
                hat
            );

            root.userData.hasGlove =
                true;
        }

        /*
         * Small, matte, non-glowing eyes -
         * glowing eyes read as robotic
         * rather than human.
         */
        const eyeMaterial =
            new THREE.MeshStandardMaterial(
                {
                    color: 0x1a1410,
                    roughness: 0.45,
                    metalness: 0.0,
                    emissive: 0x000000,
                    emissiveIntensity: 0
                }
            );

        for (
            let side = -1;
            side <= 1;
            side += 2
        ) {
            const eye =
                new THREE.Mesh(
                    new THREE.SphereGeometry(
                        0.045,
                        10,
                        8
                    ),
                    eyeMaterial
                );

            eye.position.set(
                side *
                    0.19,
                0.02,
                0.50
            );

            eye.scale.z =
                0.6;

            rig.head.add(
                eye
            );
        }

        /* ========================================================
           SHOULDERS
           ======================================================== */

        const shoulderWidth =
            1.00 *
            proportions.shoulder;

        rig.shoulderL.position.set(
            -shoulderWidth,
            0.64,
            0
        );

        rig.shoulderR.position.set(
            shoulderWidth,
            0.64,
            0
        );

        rig.chest.add(
            rig.shoulderL
        );

        rig.chest.add(
            rig.shoulderR
        );

        /* ========================================================
           ARMS
           ======================================================== */

        function setupArm(
            side
        ) {
            const shoulder =
                side === -1
                    ? rig.shoulderL
                    : rig.shoulderR;

            /*
             * Slightly different arm length
             * between dancers.
             */
            const armLength =
                index === 1
                    ? 1.48
                    : index === 3
                        ? 1.40
                        : 1.45;

            const upper =
                createLimb(
                    armLength,
                    0.235,
                    bodyMaterial
                );

            shoulder.add(
                upper
            );

            const elbow =
                side === -1
                    ? rig.elbowL
                    : rig.elbowR;

            elbow.position.y =
                -armLength;

            upper.add(
                elbow
            );

            elbow.add(
                createJoint(
                    0.20,
                    skinMaterial
                )
            );

            const forearm =
                createLimb(
                    armLength *
                        0.93,
                    0.195,
                    bodyMaterial
                );

            elbow.add(
                forearm
            );

            const hand =
                side === -1
                    ? rig.handL
                    : rig.handR;

            hand.position.y =
                -(armLength *
                    0.93);

            forearm.add(
                hand
            );

            hand.add(
                createJoint(
                    0.215,
                    skinMaterial
                )
            );

            /*
             * The tribute dancer's
             * signature single white glove.
             */
            if (
                root.userData.hasGlove &&
                side === 1
            ) {
                const glove =
                    new THREE.Mesh(
                        new THREE.SphereGeometry(
                            0.235,
                            12,
                            10
                        ),
                        new THREE.MeshStandardMaterial(
                            {
                                color: 0xf5f5f5,
                                roughness: 0.25,
                                metalness: 0.35,
                                emissive: 0xffffff,
                                emissiveIntensity: 0.12
                            }
                        )
                    );

                finalizeMesh(
                    glove
                );

                hand.add(
                    glove
                );
            }

            if (
                side === -1
            ) {
                rig.upperArmL =
                    upper;

                rig.forearmL =
                    forearm;

            } else {
                rig.upperArmR =
                    upper;

                rig.forearmR =
                    forearm;
            }
        }

        setupArm(-1);
        setupArm(1);

        /* ========================================================
           LEGS
           ======================================================== */

        function setupLeg(
            side
        ) {
            const hip =
                side === -1
                    ? rig.hipL
                    : rig.hipR;

            const hipWidth =
                0.56 *
                proportions.hip;

            hip.position.set(
                side *
                    hipWidth,
                -0.42,
                0
            );

            rig.pelvis.add(
                hip
            );

            hip.add(
                createJoint(
                    0.27,
                    clothMaterial
                )
            );

            const legLength =
                2.15 *
                proportions.leg;

            const thigh =
                createLimb(
                    legLength,
                    0.29,
                    bodyMaterial
                );

            hip.add(
                thigh
            );

            const knee =
                side === -1
                    ? rig.kneeL
                    : rig.kneeR;

            knee.position.y =
                -legLength;

            thigh.add(
                knee
            );

            knee.add(
                createJoint(
                    0.24,
                    skinMaterial
                )
            );

            const shin =
                createLimb(
                    2.06 *
                        proportions.leg,
                    0.235,
                    bodyMaterial
                );

            knee.add(
                shin
            );

            const foot =
                side === -1
                    ? rig.footL
                    : rig.footR;

            const shinLength =
                2.06 *
                proportions.leg;

            foot.position.set(
                0,
                -shinLength,
                0.24
            );

            shin.add(
                foot
            );

            const shoe =
                new THREE.Mesh(
                    new THREE.BoxGeometry(
                        0.52,
                        0.25,
                        1.00
                    ),
                    accentMaterial
                );

            shoe.position.set(
                0,
                -0.12,
                0.30
            );

            finalizeMesh(
                shoe
            );

            foot.add(
                shoe
            );

            if (
                side === -1
            ) {
                rig.thighL =
                    thigh;

                rig.shinL =
                    shin;

            } else {
                rig.thighR =
                    thigh;

                rig.shinR =
                    shin;
            }
        }

        setupLeg(-1);
        setupLeg(1);

        /* ========================================================
           CLOTHING DETAILS
           ======================================================== */

        /*
         * Different visual identity for each person.
         */
        if (
            index === 0
        ) {
            const shoulderBand =
                new THREE.Mesh(
                    new THREE.TorusGeometry(
                        0.44,
                        0.025,
                        6,
                        28
                    ),
                    accentMaterial
                );

            shoulderBand.rotation.x =
                Math.PI / 2;

            shoulderBand.position.set(
                0,
                0.10,
                0.53
            );

            rig.chest.add(
                shoulderBand
            );
        }

        if (
            index === 1
        ) {
            const chestStripe =
                new THREE.Mesh(
                    new THREE.BoxGeometry(
                        1.15,
                        0.045,
                        0.045
                    ),
                    accentMaterial
                );

            chestStripe.position.set(
                0,
                0.32,
                0.58
            );

            rig.chest.add(
                chestStripe
            );
        }

        if (
            index === 2
        ) {
            const chestStripe =
                new THREE.Mesh(
                    new THREE.BoxGeometry(
                        0.85,
                        0.045,
                        0.045
                    ),
                    accentMaterial
                );

            chestStripe.position.set(
                0,
                -0.14,
                0.58
            );

            rig.chest.add(
                chestStripe
            );
        }

        if (
            index === 3
        ) {
            const necklace =
                new THREE.Mesh(
                    new THREE.TorusGeometry(
                        0.38,
                        0.018,
                        6,
                        24
                    ),
                    accentMaterial
                );

            necklace.rotation.x =
                Math.PI / 2;

            necklace.position.set(
                0,
                0.12,
                0.50
            );

            rig.neck.add(
                necklace
            );
        }

        if (
            index === 4
        ) {
            const chestStripe =
                new THREE.Mesh(
                    new THREE.BoxGeometry(
                        0.055,
                        0.74,
                        0.045
                    ),
                    accentMaterial
                );

            chestStripe.position.set(
                0.28,
                0.0,
                0.58
            );

            rig.chest.add(
                chestStripe
            );
        }

        /*
         * Grounding halo.
         */
        const footRing =
            new THREE.Mesh(
                new THREE.TorusGeometry(
                    1.02,
                    0.018,
                    8,
                    40
                ),
                accentMaterial
            );

        footRing.rotation.x =
            Math.PI / 2;

        footRing.position.y =
            0.025;

        root.add(
            footRing
        );

        root.userData.footRing =
            footRing;

        return root;
    }

    /* ============================================================
       BASE FORMATION
       ============================================================ */

    function getBaseFormation() {
        const mobile =
            isMobile();

        if (
            mobile
        ) {
            return [
                {
                    x: -3.25,
                    z: -0.1
                },
                {
                    x: 0,
                    z: 0.7
                },
                {
                    x: 3.25,
                    z: -0.1
                }
            ];
        }

        /*
         * MUCH wider than previous versions.
         */
        return [
            {
                x: -8.4,
                z: -1.5
            },
            {
                x: -4.25,
                z: 0.0
            },
            {
                x: 0,
                z: 1.0
            },
            {
                x: 4.25,
                z: 0.0
            },
            {
                x: 8.4,
                z: -1.5
            }
        ];
    }

    /* ============================================================
       FORMATIONS
       ============================================================ */

    function getFormationPosition(
        name,
        index,
        count
    ) {
        const mobile =
            isMobile();

        const center =
            (count - 1) /
            2;

        /*
         * LINE
         */
        if (
            name === "line"
        ) {
            return {
                x:
                    (
                        index -
                        center
                    ) *
                    (
                        mobile
                            ? 3.15
                            : 4.1
                    ),

                z:
                    index ===
                    Math.floor(
                        center
                    )
                        ? 1.0
                        : -0.2
            };
        }

        /*
         * V
         */
        if (
            name === "v"
        ) {
            const distance =
                Math.abs(
                    index -
                        center
                );

            if (
                index ===
                Math.floor(center)
            ) {
                return {
                    x: 0,
                    z: 1.7
                };
            }

            const side =
                index <
                center
                    ? -1
                    : 1;

            return {
                x:
                    side *
                    distance *
                    (
                        mobile
                            ? 2.7
                            : 3.55
                    ),

                z:
                    1.7 -
                    distance *
                    1.25
            };
        }

        /*
         * ARC
         */
        if (
            name === "arc"
        ) {
            const ratio =
                count <= 1
                    ? 0
                    : index /
                        (
                            count -
                            1
                        );

            const angle =
                -Math.PI *
                    0.70 +
                ratio *
                    Math.PI *
                    1.40;

            const radius =
                mobile
                    ? 4.3
                    : 8.7;

            return {
                x:
                    Math.sin(
                        angle
                    ) *
                    radius,

                z:
                    Math.cos(
                        angle
                    ) *
                    2.2 -
                    1.5
            };
        }

        /*
         * WIDE
         */
        if (
            name === "wide"
        ) {
            return {
                x:
                    (
                        index -
                        center
                    ) *
                    (
                        mobile
                            ? 3.4
                            : 4.6
                    ),

                z:
                    Math.abs(
                        index -
                            center
                    ) *
                    -0.55
            };
        }

        /*
         * CENTER STACK.
         */
        if (
            name === "center"
        ) {
            const row =
                Math.floor(
                    index /
                        3
                );

            const col =
                index % 3;

            return {
                x:
                    (
                        col -
                        1
                    ) *
                    (
                        mobile
                            ? 2.7
                            : 3.1
                    ),

                z:
                    1.0 -
                    row *
                        1.9
            };
        }

        return {
            x: 0,
            z: 0
        };
    }

    /* ============================================================
       INDIVIDUAL MOVES
       ============================================================ */

    function moveGroove(
        target,
        t,
        phase,
        mirror
    ) {
        const a =
            t *
                Math.PI *
                2 +
            phase;

        const s =
            Math.sin(a);

        const s2 =
            Math.sin(
                a * 2
            );

        const c =
            Math.cos(a);

        target.torsoZ =
            s *
            0.13;

        target.chestX =
            s2 *
            0.07;

        target.hipLZ =
            s *
            0.20;

        target.hipRZ =
            s *
            0.20;

        target.thighLZ =
            s *
            0.08;

        target.thighRZ =
            -s *
            0.08;

        target.upperArmLX =
            -0.32 +
            s2 *
            0.20;

        target.upperArmRX =
            0.32 -
            s2 *
            0.20;

        target.forearmLX =
            0.18 +
            c *
            0.16;

        target.forearmRX =
            -0.18 -
            c *
            0.16;

        target.headZ =
            -s *
            0.07;
    }

    function moveSlide(
        target,
        t,
        phase,
        mirror
    ) {
        const a =
            t *
                Math.PI *
                2 +
            phase;

        const s =
            Math.sin(a);

        const c =
            Math.cos(a);

        target.rootX =
            s *
            0.52 *
            mirror;

        target.torsoZ =
            -s *
            0.12;

        target.chestX =
            c *
            0.05;

        target.thighLX =
            -s *
            0.20;

        target.thighRX =
            s *
            0.20;

        target.shinLX =
            Math.max(
                0,
                Math.sin(
                    a *
                        2
                )
            ) *
            0.48;

        target.shinRX =
            Math.max(
                0,
                -Math.sin(
                    a *
                        2
                )
            ) *
            0.38;

        target.upperArmLX =
            -0.50 -
            c *
            0.20;

        target.upperArmRX =
            0.50 +
            c *
            0.20;

        target.forearmLX =
            0.22;

        target.forearmRX =
            -0.22;
    }

    function moveShoulderWave(
        target,
        t,
        phase,
        mirror
    ) {
        const a =
            t *
                Math.PI *
                2 +
            phase;

        const l =
            Math.sin(a);

        const r =
            Math.sin(
                a +
                    0.72
            );

        target.shoulderLZ =
            l *
            0.30;

        target.shoulderRZ =
            -r *
            0.30;

        target.upperArmLX =
            -0.86 +
            l *
            0.40;

        target.upperArmRX =
            0.86 -
            r *
            0.40;

        target.forearmLX =
            l *
            0.52;

        target.forearmRX =
            -r *
            0.52;

        target.headZ =
            -l *
            0.09;
    }

    function moveBodyRoll(
        target,
        t,
        phase
    ) {
        const a =
            t *
                Math.PI *
                2 +
            phase;

        const s =
            Math.sin(a);

        const c =
            Math.cos(a);

        target.chestX =
            s *
            0.22;

        target.torsoX =
            -s *
            0.15;

        target.headX =
            -s *
            0.13;

        target.hipLZ =
            s *
            0.22;

        target.hipRZ =
            s *
            0.22;

        target.shoulderLZ =
            c *
            0.18;

        target.shoulderRZ =
            -c *
            0.18;

        target.upperArmLX =
            -0.48 +
            s *
            0.20;

        target.upperArmRX =
            0.48 -
            s *
            0.20;
    }

    function moveFootSwitch(
        target,
        t,
        phase,
        mirror
    ) {
        const a =
            t *
                Math.PI *
                4 +
            phase;

        const s =
            Math.sin(a);

        const c =
            Math.cos(a);

        target.rootX =
            s *
            0.22;

        target.thighLX =
            s *
            0.31;

        target.thighRX =
            -s *
            0.31;

        target.shinLX =
            Math.max(
                0,
                c
            ) *
            0.55;

        target.shinRX =
            Math.max(
                0,
                -c
            ) *
            0.55;

        target.footLX =
            c *
            0.10;

        target.footRX =
            -c *
            0.10;

        target.upperArmLX =
            -0.48 -
            s *
            0.15;

        target.upperArmRX =
            0.48 +
            s *
            0.15;

        target.forearmLX =
            c *
            0.24;

        target.forearmRX =
            -c *
            0.24;
    }

    function moveShuffle(
        target,
        t,
        phase
    ) {
        const a =
            t *
                Math.PI *
                5 +
            phase;

        const s =
            Math.sin(a);

        const c =
            Math.cos(a);

        target.rootX =
            s *
            0.32;

        target.thighLX =
            s *
            0.27;

        target.thighRX =
            -s *
            0.27;

        target.shinLX =
            Math.max(
                0,
                c
            ) *
            0.45;

        target.shinRX =
            Math.max(
                0,
                -c
            ) *
            0.45;

        target.upperArmLX =
            -0.44 -
            s *
            0.22;

        target.upperArmRX =
            0.44 +
            s *
            0.22;

        target.forearmLX =
            c *
            0.28;

        target.forearmRX =
            -c *
            0.28;

        target.headZ =
            s *
            0.06;
    }

    function movePower(
        target,
        t,
        phase,
        mirror
    ) {
        /*
         * Fast hit.
         */
        const wave =
            Math.sin(
                t *
                    Math.PI *
                    4 +
                    phase
            );

        const hit =
            Math.pow(
                Math.max(
                    0,
                    wave
                ),
                6
            );

        target.chestX =
            -0.18 *
            hit;

        target.upperArmLX =
            -1.02 -
            hit *
                0.30;

        target.upperArmRX =
            1.02 +
            hit *
                0.30;

        target.forearmLX =
            0.45;

        target.forearmRX =
            -0.45;

        target.headX =
            0.10 *
            hit;

        target.thighLX =
            -0.20 *
            hit;

        target.thighRX =
            0.20 *
            hit;
    }

    function moveIsolation(
        target,
        t,
        phase
    ) {
        const a =
            t *
                Math.PI *
                6 +
            phase;

        const s =
            Math.sin(a);

        const c =
            Math.cos(a);

        target.headZ =
            s *
            0.15;

        target.headX =
            c *
            0.07;

        target.chestY =
            s *
            0.12;

        target.torsoY =
            -s *
            0.14;

        target.forearmLX =
            s *
            0.34;

        target.forearmRX =
            -s *
            0.34;

        target.upperArmLX =
            -0.46;

        target.upperArmRX =
            0.46;
    }

    function moveTurn(
        target,
        t,
        phase,
        mirror
    ) {
        /*
         * Controlled turn.
         */
        target.rootYRot =
            easeInOut(t) *
            Math.PI *
            2 *
            mirror;

        const arm =
            Math.sin(
                t *
                    Math.PI
            );

        target.upperArmLX =
            -0.98 -
            arm *
                0.20;

        target.upperArmRX =
            0.98 +
            arm *
                0.20;

        target.forearmLX =
            0.23;

        target.forearmRX =
            -0.23;

        target.thighLX =
            0.10;

        target.thighRX =
            -0.10;
    }

    function moveMoonwalk(
        target,
        t,
        phase,
        mirror
    ) {
        /*
         * MJ-style backward glide:
         * net backward travel while
         * the feet alternate as if
         * walking forward.
         */
        const glide =
            easeInOut(t);

        target.rootZ =
            -glide *
            1.55;

        target.rootYRot =
            0.05 *
            mirror;

        const shuffle =
            Math.sin(
                t *
                    Math.PI *
                    7 +
                phase
            );

        const shuffle2 =
            Math.sin(
                t *
                    Math.PI *
                    7 +
                phase +
                    Math.PI
            );

        target.thighLX =
            0.16 +
            shuffle *
            0.22;

        target.thighRX =
            -0.10 -
            shuffle2 *
            0.18;

        target.shinLX =
            Math.max(
                0,
                -shuffle
            ) *
            0.55;

        target.shinRX =
            Math.max(
                0,
                shuffle2
            ) *
            0.42;

        target.footLZ =
            shuffle *
            0.30;

        target.footRZ =
            -shuffle2 *
            0.24;

        target.torsoX =
            0.10;

        target.chestX =
            0.08;

        target.headZ =
            0.14 *
            mirror;

        target.headX =
            -0.05;

        /*
         * One hand toward the hat brim,
         * the other trailing low - the
         * signature silhouette.
         */
        target.upperArmLX =
            -1.35;

        target.forearmLX =
            0.85;

        target.upperArmRX =
            0.55 +
            shuffle *
            0.08;

        target.forearmRX =
            -0.20;
    }

    function movePose(
        target,
        t,
        phase,
        mirror
    ) {
        const pulse =
            Math.sin(
                t *
                    Math.PI *
                    2
            );

        target.torsoZ =
            -0.08 *
            mirror;

        target.chestX =
            -0.06;

        target.headZ =
            0.10;

        target.upperArmLX =
            -1.02;

        target.upperArmRX =
            0.78;

        target.forearmLX =
            0.27;

        target.forearmRX =
            -0.54;

        target.thighLX =
            -0.15;

        target.thighRX =
            0.25;

        target.shinRX =
            0.26;

        target.rootX =
            pulse *
            0.05;
    }

    /* ============================================================
       INDIVIDUAL DISPATCH
       ============================================================ */

    function applyIndividualMove(
        target,
        move,
        t,
        phase,
        mirror,
        personality
    ) {
        resetPose(
            target
        );

        switch (
            move
        ) {
            case "groove":
                moveGroove(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;

            case "slide":
                moveSlide(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;

            case "shoulderWave":
                moveShoulderWave(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;

            case "bodyRoll":
                moveBodyRoll(
                    target,
                    t,
                    phase
                );
                break;

            case "footSwitch":
                moveFootSwitch(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;

            case "shuffle":
                moveShuffle(
                    target,
                    t,
                    phase
                );
                break;

            case "power":
                movePower(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;

            case "isolation":
                moveIsolation(
                    target,
                    t,
                    phase
                );
                break;

            case "turn":
                moveTurn(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;

            case "pose":
                movePose(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;

            case "moonwalk":
                moveMoonwalk(
                    target,
                    t,
                    phase,
                    mirror
                );
                break;
        }

        /*
         * PERSONALITY
         */
        if (
            personality ===
            "hero"
        ) {
            target.chestX *=
                1.05;

            target.headX *=
                1.05;
        }

        if (
            personality ===
            "groover"
        ) {
            target.hipLZ *=
                1.18;

            target.hipRZ *=
                1.18;

            target.torsoZ *=
                1.08;
        }

        if (
            personality ===
            "smooth"
        ) {
            target.torsoX *=
                0.70;

            target.chestX *=
                0.84;

            target.headX *=
                0.80;
        }

        if (
            personality ===
            "power"
        ) {
            target.chestX *=
                1.16;

            target.upperArmLX *=
                1.10;

            target.upperArmRX *=
                1.10;
        }

        if (
            personality ===
            "wild"
        ) {
            target.headZ *=
                1.35;

            target.shoulderLZ *=
                1.18;

            target.shoulderRZ *=
                1.18;
        }

        /*
         * Beat punch:
         * body only.
         */
        if (
            beatPulse >
            0.15
        ) {
            const hit =
                beatPulse *
                0.11;

            target.chestX -=
                hit;

            target.headX +=
                hit *
                0.28;

            target.upperArmLX -=
                hit;

            target.upperArmRX +=
                hit;
        }
    }

    /* ============================================================
       GROUP MOVES
       ============================================================ */

    function groupBounce(
        target,
        t,
        phase,
        mirror,
        index
    ) {
        const a =
            t *
                Math.PI *
                4;

        const s =
            Math.sin(a);

        target.torsoX =
            s *
            0.07;

        target.chestX =
            Math.sin(
                a * 2
            ) *
            0.09;

        target.upperArmLX =
            -0.46 +
            s *
            0.12;

        target.upperArmRX =
            0.46 -
            s *
            0.12;

        target.forearmLX =
            0.20;

        target.forearmRX =
            -0.20;

        target.thighLX =
            s *
            0.13;

        target.thighRX =
            -s *
            0.13;
    }

    function groupArms(
        target,
        t,
        phase,
        mirror,
        index
    ) {
        const a =
            t *
                Math.PI *
                2;

        const wave =
            Math.sin(
                a +
                    index *
                        0.08
            );

        target.upperArmLX =
            -0.86 +
            wave *
            0.30;

        target.upperArmRX =
            0.86 -
            wave *
            0.30;

        target.forearmLX =
            wave *
            0.50;

        target.forearmRX =
            -wave *
            0.50;

        target.shoulderLZ =
            wave *
            0.24;

        target.shoulderRZ =
            -wave *
            0.24;

        target.headZ =
            -wave *
            0.08;
    }

    function groupStep(
        target,
        t,
        phase,
        mirror,
        index
    ) {
        const a =
            t *
                Math.PI *
                2;

        const s =
            Math.sin(
                a +
                    index *
                        0.12
            );

        const c =
            Math.cos(
                a +
                    index *
                        0.12
            );

        const side =
            index % 2 ===
            0
                ? 1
                : -1;

        target.rootX =
            s *
            0.30 *
            side;

        target.thighLX =
            -s *
            0.24;

        target.thighRX =
            s *
            0.24;

        target.shinLX =
            Math.max(
                0,
                c
            ) *
            0.48;

        target.shinRX =
            Math.max(
                0,
                -c
            ) *
            0.48;

        target.upperArmLX =
            -0.50 -
            c *
            0.17;

        target.upperArmRX =
            0.50 +
            c *
            0.17;

        target.forearmLX =
            0.23;

        target.forearmRX =
            -0.23;

        target.torsoZ =
            -s *
            0.12;
    }

    function groupWave(
        target,
        t,
        phase,
        mirror,
        index
    ) {
        /*
         * Traveling wave:
         * each person follows the previous
         * one with a tiny delay.
         */
        const a =
            t *
                Math.PI *
                2 +
            index *
                0.38;

        const wave =
            Math.sin(a);

        target.shoulderLZ =
            wave *
            0.34;

        target.shoulderRZ =
            -wave *
            0.34;

        target.upperArmLX =
            -0.82 +
            wave *
            0.40;

        target.upperArmRX =
            0.82 -
            wave *
            0.40;

        target.forearmLX =
            wave *
            0.48;

        target.forearmRX =
            -wave *
            0.48;

        target.chestZ =
            wave *
            0.11;

        target.headZ =
            -wave *
            0.08;
    }

    function groupPower(
        target,
        t,
        phase,
        mirror,
        index
    ) {
        const wave =
            Math.sin(
                t *
                    Math.PI *
                    4
            );

        const hit =
            Math.pow(
                Math.max(
                    0,
                    wave
                ),
                5
            );

        target.chestX =
            -0.16 *
            hit;

        target.upperArmLX =
            -1.00 -
            hit *
                0.22;

        target.upperArmRX =
            1.00 +
            hit *
                0.22;

        target.forearmLX =
            0.45;

        target.forearmRX =
            -0.45;

        target.headX =
            0.09 *
            hit;

        target.thighLX =
            -0.18 *
            hit;

        target.thighRX =
            0.18 *
            hit;
    }

    function groupPose(
        target,
        t,
        phase,
        mirror,
        index
    ) {
        const side =
            index % 2 ===
            0
                ? 1
                : -1;

        const pulse =
            Math.sin(
                t *
                    Math.PI *
                    2
            );

        target.chestZ =
            -0.08;

        target.headZ =
            0.10;

        target.upperArmLX =
            -0.98 *
            side;

        target.upperArmRX =
            0.74 *
            side;

        target.forearmLX =
            0.27 *
            side;

        target.forearmRX =
            -0.50 *
            side;

        target.thighLX =
            -0.14;

        target.thighRX =
            0.24;

        target.rootX =
            pulse *
            0.035;
    }

    function groupHit(
        target,
        t,
        phase,
        mirror,
        index
    ) {
        const hit =
            Math.sin(
                t *
                    Math.PI
            );

        const amount =
            index === 2
                ? 1.12
                : 1;

        target.chestX =
            -0.17 *
            hit;

        target.upperArmLX =
            -1.14 *
            hit *
            amount;

        target.upperArmRX =
            1.14 *
            hit *
            amount;

        target.forearmLX =
            0.43 *
            hit;

        target.forearmRX =
            -0.43 *
            hit;

        target.headX =
            0.08 *
            hit;

        target.thighLX =
            -0.18 *
            hit;

        target.thighRX =
            0.18 *
            hit;
    }

    function applyGroupMove(
        target,
        move,
        t,
        phase,
        mirror,
        index
    ) {
        resetPose(
            target
        );

        switch (
            move
        ) {
            case "bounce":
                groupBounce(
                    target,
                    t,
                    phase,
                    mirror,
                    index
                );
                break;

            case "arms":
                groupArms(
                    target,
                    t,
                    phase,
                    mirror,
                    index
                );
                break;

            case "step":
                groupStep(
                    target,
                    t,
                    phase,
                    mirror,
                    index
                );
                break;

            case "wave":
                groupWave(
                    target,
                    t,
                    phase,
                    mirror,
                    index
                );
                break;

            case "power":
                groupPower(
                    target,
                    t,
                    phase,
                    mirror,
                    index
                );
                break;

            case "pose":
                groupPose(
                    target,
                    t,
                    phase,
                    mirror,
                    index
                );
                break;

            case "hit":
                groupHit(
                    target,
                    t,
                    phase,
                    mirror,
                    index
                );
                break;
        }

        if (
            beatPulse >
            0.16
        ) {
            const hit =
                beatPulse *
                0.10;

            target.chestX -=
                hit;

            target.headX +=
                hit *
                0.25;
        }
    }

    /* ============================================================
       DANCER INITIALIZATION
       ============================================================ */

    function createDancers() {
        const count =
            isMobile()
                ? CONFIG.mobile.dancers
                : CONFIG.desktop.dancers;

        const base =
            getBaseFormation();

        for (
            let i = 0;
            i < count;
            i++
        ) {
            const dancer =
                createDancer(
                    i,
                    CONFIG.colors[
                        i %
                            CONFIG.colors
                                .length
                    ]
                );

            const basePosition =
                base[i];

            dancer.position.set(
                basePosition.x,
                0,
                basePosition.z
            );

            /*
             * Different visible sizes.
             */
            const visualScale =
                i === 0
                    ? isMobile()
                        ? 0.84
                        : 1.04
                    : i === 2
                        ? isMobile()
                            ? 0.67
                            : 0.90
                        : i >= 3
                            ? isMobile()
                                ? 0.62
                                : 0.82
                            : isMobile()
                                ? 0.70
                                : 0.88;

            dancer.scale.setScalar(
                visualScale
            );

            dancer.userData.baseScale =
                visualScale;

            dancer.userData.basePosition =
                {
                    x: basePosition.x,
                    z: basePosition.z
                };

            /*
             * Every dancer starts
             * with a different move.
             */
            dancer.userData.move =
                INDIVIDUAL_MOVES[
                    (
                        i * 2 +
                        individualRound
                    ) %
                    INDIVIDUAL_MOVES.length
                ];

            dancer.userData.moveTimer =
                random(
                    0,
                    0.9
                );

            dancer.userData.moveDuration =
                random(
                    CONFIG.choreography
                        .moveMin,
                    CONFIG.choreography
                        .moveMax
                );

            dancer.userData.speed =
                random(
                    0.72,
                    1.28
                );

            scene.add(
                dancer
            );

            dancers.push(
                dancer
            );
        }
    }

    /* ============================================================
       INDIVIDUAL DANCE UPDATE
       ============================================================ */

    function updateIndividualDancers(
        delta,
        elapsed
    ) {
        dancers.forEach(
            (
                dancer,
                index
            ) => {
                const rig =
                    dancer.userData.rig;

                /*
                 * Ease back to normal size
                 * whenever we're not in the
                 * solo spotlight.
                 */
                if (
                    performanceMode !==
                        "solo" &&
                    dancer.userData
                        .baseScale
                ) {
                    dancer.scale.setScalar(
                        damp(
                            dancer.scale
                                .x,
                            dancer.userData
                                .baseScale,
                            4.0,
                            delta
                        )
                    );
                }

                dancer.userData.moveTimer +=
                    delta *
                    dancer.userData.speed;

                /*
                 * Switch moves independently.
                 */
                if (
                    dancer.userData
                        .moveTimer >=
                    dancer.userData
                        .moveDuration
                ) {
                    dancer.userData
                        .moveTimer = 0;

                    dancer.userData.moveDuration =
                        random(
                            CONFIG.choreography
                                .moveMin,
                            CONFIG.choreography
                                .moveMax
                        );

                    const style =
                        dancer.userData
                            .personality;

                    let choices =
                        INDIVIDUAL_MOVES;

                    if (
                        style === "hero"
                    ) {
                        choices = [
                            "groove",
                            "bodyRoll",
                            "power",
                            "turn",
                            "pose",
                            "moonwalk",
                            "moonwalk"
                        ];
                    }

                    if (
                        style === "groover"
                    ) {
                        choices = [
                            "groove",
                            "slide",
                            "footSwitch",
                            "shuffle"
                        ];
                    }

                    if (
                        style === "smooth"
                    ) {
                        choices = [
                            "bodyRoll",
                            "shoulderWave",
                            "slide",
                            "pose"
                        ];
                    }

                    if (
                        style === "power"
                    ) {
                        choices = [
                            "power",
                            "footSwitch",
                            "turn",
                            "shuffle"
                        ];
                    }

                    if (
                        style === "wild"
                    ) {
                        choices = [
                            "shuffle",
                            "isolation",
                            "shoulderWave",
                            "power",
                            "footSwitch"
                        ];
                    }

                    dancer.userData.move =
                        randomChoice(
                            choices
                        );

                    dancer.userData.speed =
                        random(
                            0.62,
                            1.42
                        );

                    dancer.userData.phase =
                        random(
                            -0.4,
                            0.4
                        );
                }

                const duration =
                    dancer.userData
                        .moveDuration;

                let t =
                    dancer.userData
                        .moveTimer /
                    duration;

                t =
                    clamp(
                        t,
                        0,
                        1
                    );

                /*
                 * Speed changes through
                 * the phrase itself.
                 */
                const acceleration =
                    lerp(
                        0.78,
                        1.25,
                        Math.sin(
                            t *
                                Math.PI
                        )
                    );

                const motionT =
                    clamp(
                        (
                            t *
                            acceleration
                        ),
                        0,
                        1
                    );

                applyIndividualMove(
                    rig.target,
                    dancer.userData.move,
                    motionT,
                    dancer.userData.phase,
                    dancer.userData.mirror,
                    dancer.userData.personality
                );

                /*
                 * Slight timing difference.
                 */
                if (
                    index !== 0
                ) {
                    const micro =
                        Math.sin(
                            elapsed *
                                (
                                    1.8 +
                                    index *
                                        0.12
                                ) +
                                dancer
                                    .userData
                                    .phase
                        );

                    rig.target.headZ +=
                        micro *
                        0.018;

                    rig.target.chestZ +=
                        micro *
                        0.015;
                }

                applyPose(
                    rig,
                    rig.target,
                    delta
                );

                /*
                 * applyPose damps the dancer's
                 * top-level position toward the
                 * pose's small local sway
                 * (rootX/rootZ). Without
                 * re-anchoring, every dancer
                 * drifts toward that same small
                 * value and they collapse into
                 * one spot. Pull back toward this
                 * dancer's own stage position,
                 * the same way group mode
                 * re-anchors to its formation.
                 */
                if (
                    dancer.userData
                        .basePosition
                ) {
                    dancer.position.x =
                        damp(
                            dancer.position
                                .x,
                            dancer.userData
                                .basePosition
                                .x,
                            5.0,
                            delta
                        );

                    dancer.position.z =
                        damp(
                            dancer.position
                                .z,
                            dancer.userData
                                .basePosition
                                .z,
                            5.0,
                            delta
                        );
                }

                /*
                 * Natural breathing.
                 */
                rig.torso.position.y =
                    0.34 +
                    Math.sin(
                        elapsed *
                            1.85 +
                            dancer
                                .userData
                                .phase
                    ) *
                    0.008;

                /*
                 * Ground ring.
                 */
                if (
                    dancer.userData
                        .footRing
                ) {
                    dancer.userData
                        .footRing
                        .scale.setScalar(
                            1 +
                                overallEnergy *
                                    0.04 +
                                beatPulse *
                                    0.10
                        );
                }
            }
        );
    }

    /* ============================================================
       GROUP DANCE UPDATE
       ============================================================ */

    function updateGroupDancers(
        delta,
        elapsed
    ) {
        const formation =
            FORMATIONS[
                currentFormation
            ];

        dancers.forEach(
            (
                dancer,
                index
            ) => {
                const rig =
                    dancer.userData.rig;

                if (
                    dancer.userData
                        .baseScale
                ) {
                    dancer.scale.setScalar(
                        damp(
                            dancer.scale
                                .x,
                            dancer.userData
                                .baseScale,
                            4.0,
                            delta
                        )
                    );
                }

                /*
                 * One shared motion with
                 * tiny phase delays.
                 */
                const local =
                    (
                        performanceTimer /
                        1.55 +
                        index *
                            0.055
                    ) % 1;

                applyGroupMove(
                    rig.target,
                    GROUP_MOVES[
                        groupRound %
                            GROUP_MOVES.length
                    ],
                    local,
                    index *
                        0.12,
                    dancer.userData
                        .mirror,
                    index
                );

                /*
                 * Hero remains visually
                 * slightly stronger.
                 */
                if (
                    index === 2 &&
                    dancers.length >= 5
                ) {
                    rig.target.chestX *=
                        1.07;

                    rig.target.upperArmLX *=
                        1.06;

                    rig.target.upperArmRX *=
                        1.06;
                }

                applyPose(
                    rig,
                    rig.target,
                    delta
                );

                /*
                 * Formation movement.
                 */
                const target =
                    getFormationPosition(
                        formation,
                        index,
                        dancers.length
                    );

                dancer.position.x =
                    damp(
                        dancer.position.x,
                        target.x,
                        5.0,
                        delta
                    );

                dancer.position.z =
                    damp(
                        dancer.position.z,
                        target.z,
                        5.0,
                        delta
                    );

                /*
                 * Slight body breathing.
                 */
                rig.torso.position.y =
                    0.34 +
                    Math.sin(
                        elapsed *
                            1.8 +
                            index *
                                0.30
                    ) *
                    0.007;
            }
        );
    }

    /* ============================================================
       PERFORMANCE DIRECTOR
       ============================================================ */

    function updatePerformance(
        delta,
        elapsed
    ) {
        performanceTimer +=
            delta;

        if (
            performanceMode ===
            "individual"
        ) {
            if (
                performanceTimer >=
                CONFIG.choreography
                    .individualDuration
            ) {
                performanceMode =
                    "group";

                performanceTimer =
                    0;

                groupRound =
                    (
                        groupRound +
                        1
                    ) %
                    GROUP_MOVES.length;

                currentFormation =
                    (
                        currentFormation +
                        1
                    ) %
                    FORMATIONS.length;
            }

            updateIndividualDancers(
                delta,
                elapsed
            );

        } else if (
            performanceMode ===
            "group"
        ) {
            if (
                performanceTimer >=
                CONFIG.choreography
                    .groupDuration
            ) {
                performanceTimer =
                    0;

                /*
                 * Every other group
                 * phase hands off to a
                 * featured solo instead
                 * of straight back to
                 * the individual phase.
                 */
                soloCycles =
                    (
                        soloCycles +
                        1
                    ) % 2;

                if (
                    soloCycles === 0
                ) {
                    performanceMode =
                        "solo";

                    soloIndex =
                        (
                            soloIndex +
                            1
                        ) %
                        dancers.length;

                } else {
                    performanceMode =
                        "individual";

                    individualRound =
                        (
                            individualRound +
                            1
                        ) %
                        INDIVIDUAL_MOVES.length;

                    /*
                     * Each dancer restarts
                     * with a new identity.
                     */
                    dancers.forEach(
                        (
                            dancer,
                            index
                        ) => {
                            dancer.userData.move =
                                INDIVIDUAL_MOVES[
                                    (
                                        individualRound +
                                        index *
                                            2
                                    ) %
                                    INDIVIDUAL_MOVES.length
                                ];

                            dancer.userData
                                .moveTimer =
                                random(
                                    0,
                                    0.35
                                );
                        }
                    );
                }
            }

            updateGroupDancers(
                delta,
                elapsed
            );

        } else {
            /*
             * SOLO SPOTLIGHT
             */
            if (
                performanceTimer >=
                CONFIG.choreography
                    .soloDuration
            ) {
                performanceMode =
                    "individual";

                performanceTimer =
                    0;

                individualRound =
                    (
                        individualRound +
                        1
                    ) %
                    INDIVIDUAL_MOVES.length;

                dancers.forEach(
                    (
                        dancer,
                        index
                    ) => {
                        dancer.userData.move =
                            INDIVIDUAL_MOVES[
                                (
                                    individualRound +
                                    index *
                                        2
                                ) %
                                INDIVIDUAL_MOVES.length
                            ];

                        dancer.userData
                            .moveTimer =
                            random(
                                0,
                                0.35
                            );
                    }
                );
            }

            updateSoloDancers(
                delta,
                elapsed
            );
        }
    }

    /* ============================================================
       SOLO DANCE UPDATE
       ============================================================ */

    function updateSoloDancers(
        delta,
        elapsed
    ) {
        /*
         * Reuses each dancer's own
         * personal choreography, then
         * pushes the featured dancer
         * forward into the spotlight
         * while the rest fall back.
         */
        updateIndividualDancers(
            delta,
            elapsed
        );

        const soloDancer =
            dancers[
                soloIndex %
                    dancers.length
            ];

        dancers.forEach(
            dancer => {
                const isSolo =
                    dancer ===
                    soloDancer;

                const base =
                    dancer.userData
                        .basePosition ||
                    {
                        x: 0,
                        z: 0
                    };

                const baseScale =
                    dancer.userData
                        .baseScale ||
                    1;

                const targetX =
                    isSolo
                        ? 0
                        : base.x +
                          (
                              base.x >=
                              0
                                  ? 3.5
                                  : -3.5
                          );

                const targetZ =
                    isSolo
                        ? base.z +
                          4.2
                        : base.z -
                          3.2;

                const targetScale =
                    isSolo
                        ? baseScale *
                          1.35
                        : baseScale *
                          0.55;

                dancer.position.x =
                    damp(
                        dancer.position
                            .x,
                        targetX,
                        4.2,
                        delta
                    );

                dancer.position.z =
                    damp(
                        dancer.position
                            .z,
                        targetZ,
                        4.2,
                        delta
                    );

                dancer.scale.setScalar(
                    damp(
                        dancer.scale.x,
                        targetScale,
                        4.2,
                        delta
                    )
                );
            }
        );
    }

    /* ============================================================
       PARTICLE FIELD
       ============================================================ */

    function createParticleField() {
        const count =
            isMobile()
                ? CONFIG.mobile.particles
                : CONFIG.desktop.particles;

        const positions =
            new Float32Array(
                count * 3
            );

        const velocities =
            new Float32Array(
                count
            );

        for (
            let i = 0;
            i < count;
            i++
        ) {
            const i3 =
                i * 3;

            positions[i3] =
                random(
                    -58,
                    58
                );

            positions[i3 + 1] =
                random(
                    -16,
                    28
                );

            positions[i3 + 2] =
                random(
                    -110,
                    25
                );

            velocities[i] =
                random(
                    3.0,
                    6.0
                );
        }

        const geometry =
            new THREE.BufferGeometry();

        geometry.setAttribute(
            "position",
            new THREE.BufferAttribute(
                positions,
                3
            )
        );

        particleField =
            new THREE.Points(
                geometry,
                new THREE.PointsMaterial({
                    color: 0xaaa4e8,

                    size:
                        isMobile()
                            ? 0.06
                            : 0.085,

                    transparent: true,

                    opacity: 0.46,

                    depthWrite:
                        false,

                    blending:
                        THREE.AdditiveBlending
                })
            );

        particleData = {
            velocities
        };

        scene.add(
            particleField
        );
    }

    function updateParticleField(
        delta,
        elapsed
    ) {
        if (
            !particleField
        ) {
            return;
        }

        const positions =
            particleField
                .geometry
                .attributes
                .position
                .array;

        const velocities =
            particleData
                .velocities;

        const count =
            positions.length /
            3;

        for (
            let i = 0;
            i < count;
            i++
        ) {
            const i3 =
                i * 3;

            positions[
                i3 + 2
            ] +=
                (
                    velocities[i] +
                    overallEnergy *
                        30 +
                    beatPulse *
                        34
                ) *
                delta;

            positions[i3] +=
                Math.sin(
                    elapsed *
                        0.20 +
                        i
                ) *
                0.002;

            if (
                positions[
                    i3 + 2
                ] > 25
            ) {
                positions[
                    i3 + 2
                ] = -108;

                positions[i3] =
                    random(
                        -58,
                        58
                    );

                positions[
                    i3 + 1
                ] =
                    random(
                        -16,
                        28
                    );
            }
        }

        particleField
            .geometry
            .attributes
            .position
            .needsUpdate =
            true;

        particleField.material.opacity =
            0.36 +
            overallEnergy *
                0.16 +
            beatPulse *
                0.14;
    }

    /* ============================================================
       FLYING DEPTH OBJECTS
       ============================================================ */

    function createFlyingObjects() {
        const count =
            isMobile()
                ? CONFIG.mobile
                      .flyingObjects
                : CONFIG.desktop
                      .flyingObjects;

        for (
            let i = 0;
            i < count;
            i++
        ) {
            const group =
                new THREE.Group();

            const color =
                CONFIG.colors[
                    i %
                        CONFIG.colors
                            .length
                ];

            let mesh;

            if (
                i % 9 ===
                8
            ) {
                /*
                 * Occasional big portal ring -
                 * the camera flies straight
                 * through its center.
                 */
                mesh =
                    new THREE.Mesh(
                        new THREE.TorusGeometry(
                            random(
                                3.2,
                                5.2
                            ),
                            0.09,
                            10,
                            48
                        ),
                        new THREE.MeshBasicMaterial({
                            color,

                            transparent:
                                true,

                            opacity:
                                0.55,

                            blending:
                                THREE.AdditiveBlending
                        })
                    );

            } else if (
                i % 4 ===
                0
            ) {
                mesh =
                    new THREE.Mesh(
                        new THREE.OctahedronGeometry(
                            random(
                                0.10,
                                0.24
                            ),
                            1
                        ),
                        new THREE.MeshBasicMaterial({
                            color,

                            transparent:
                                true,

                            opacity:
                                0.46,

                            blending:
                                THREE.AdditiveBlending
                        })
                    );

            } else if (
                i % 4 ===
                1
            ) {
                mesh =
                    new THREE.Mesh(
                        new THREE.TorusGeometry(
                            random(
                                0.17,
                                0.29
                            ),
                            0.016,
                            8,
                            28
                        ),
                        new THREE.MeshBasicMaterial({
                            color,

                            transparent:
                                true,

                            opacity:
                                0.48,

                            blending:
                                THREE.AdditiveBlending
                        })
                    );

            } else if (
                i % 4 ===
                2
            ) {
                mesh =
                    new THREE.Mesh(
                        new THREE.TetrahedronGeometry(
                            random(
                                0.12,
                                0.25
                            ),
                            0
                        ),
                        new THREE.MeshBasicMaterial({
                            color,

                            transparent:
                                true,

                            opacity:
                                0.42,

                            blending:
                                THREE.AdditiveBlending
                        })
                    );

            } else {
                mesh =
                    new THREE.Mesh(
                        new THREE.BoxGeometry(
                            random(
                                0.15,
                                0.28
                            ),
                            random(
                                0.15,
                                0.28
                            ),
                            random(
                                0.15,
                                0.28
                            )
                        ),
                        new THREE.MeshBasicMaterial({
                            color,

                            transparent:
                                true,

                            opacity:
                                0.40,

                            blending:
                                THREE.AdditiveBlending
                        })
                    );
            }

            group.add(
                mesh
            );

            const isPortal =
                i % 9 === 8;

            /*
             * A comet-style trail streak.
             * Kept as a sibling in the scene
             * (not a child of the tumbling
             * group) so it always stays
             * aligned backward along the
             * flight path instead of
             * spinning with the shape.
             */
            const trail =
                new THREE.Mesh(
                    new THREE.CylinderGeometry(
                        0.006,
                        isPortal
                            ? 0.10
                            : 0.05,
                        1,
                        8,
                        1,
                        true
                    ),
                    new THREE.MeshBasicMaterial(
                        {
                            color,
                            transparent: true,
                            opacity:
                                isPortal
                                    ? 0.30
                                    : 0.40,
                            blending:
                                THREE.AdditiveBlending,
                            depthWrite: false,
                            side: THREE.DoubleSide
                        }
                    )
                );

            trail.rotation.x =
                Math.PI / 2;

            scene.add(
                trail
            );

            group.userData.trail =
                trail;

            group.position.set(
                isPortal
                    ? random(
                          -2.5,
                          2.5
                      )
                    : random(
                          -17,
                          17
                      ),
                isPortal
                    ? random(
                          5,
                          8
                      )
                    : random(
                          -5,
                          18
                      ),
                random(
                    -46,
                    -10
                )
            );

            group.userData.baseX =
                group.position.x;

            group.userData.baseY =
                group.position.y;

            group.userData.phase =
                Math.random() *
                Math.PI *
                2;

            group.userData.speed =
                isPortal
                    ? random(
                          5,
                          8
                      )
                    : random(
                          6,
                          10
                      );

            group.userData.spin =
                random(
                    -1.8,
                    1.8
                );

            group.userData.isPortal =
                isPortal;

            group.scale.setScalar(
                random(
                    0.9,
                    2.3
                )
            );

            const trailLength =
                group.userData.speed *
                0.22;

            trail.scale.set(
                group.scale.x,
                trailLength,
                group.scale.x
            );

            group.userData.trailHalf =
                trailLength / 2;

            scene.add(
                group
            );

            flyingObjects.push(
                group
            );
        }
    }

    function resetFlyingObject(
        object
    ) {
        const isPortal =
            object.userData.isPortal;

        object.position.x =
            isPortal
                ? random(
                      -2.5,
                      2.5
                  )
                : random(
                      -18,
                      18
                  );

        object.position.y =
            isPortal
                ? random(
                      5,
                      8
                  )
                : random(
                      -5,
                      18
                  );

        object.userData.baseX =
            object.position.x;

        object.userData.baseY =
            object.position.y;

        object.position.z =
            random(
                -46,
                -22
            );

        object.scale.setScalar(
            random(
                0.9,
                2.3
            )
        );

        if (
            object.userData.trail
        ) {
            object.userData.trail.scale.x =
                object.scale.x;

            object.userData.trail.scale.z =
                object.scale.x;
        }

        /*
         * Retint to the current scene's
         * palette - each reset nudges the
         * whole field toward the new
         * scene's look.
         */
        const scenePalette =
            SCENES[
                sceneMode
            ].colors;

        const newColor =
            randomChoice(
                scenePalette
            );

        const shapeMesh =
            object.children[0];

        if (
            shapeMesh &&
            shapeMesh.material
        ) {
            shapeMesh.material.color.setHex(
                newColor
            );

            if (
                shapeMesh.material
                    .emissive
            ) {
                shapeMesh.material.emissive.setHex(
                    newColor
                );
            }
        }

        if (
            object.userData.trail
        ) {
            object.userData.trail.material.color.setHex(
                newColor
            );
        }
    }

    function updateFlyingObjects(
        delta,
        elapsed
    ) {
        flyingObjects.forEach(
            object => {
                /*
                 * Cruise speed is deliberately
                 * slow - the show only really
                 * takes off once the song is
                 * actually playing (overallEnergy
                 * / beatPulse come straight from
                 * the audio analyser and fall
                 * back to ~0 when paused/silent).
                 */
                const speed =
                    (
                        object.userData
                            .speed +
                        overallEnergy *
                            34 +
                        beatPulse *
                            46
                    ) *
                    SCENES[
                        sceneMode
                    ].speedMult;

                object.position.z +=
                    speed *
                    delta;

                /*
                 * Side drift.
                 */
                object.position.x =
                    object.userData
                        .baseX +
                    Math.sin(
                        elapsed *
                            0.38 +
                            object.userData
                                .phase
                    ) *
                    (
                        0.5 +
                        overallEnergy
                    );

                object.position.y =
                    object.userData
                        .baseY +
                    Math.cos(
                        elapsed *
                            0.30 +
                            object.userData
                                .phase
                    ) *
                    0.55;

                object.rotation.x +=
                    object.userData
                        .spin *
                    delta;

                object.rotation.y +=
                    object.userData
                        .spin *
                    0.75 *
                    delta;

                /*
                 * Cross viewer plane.
                 */
                if (
                    object.position.z >
                    25
                ) {
                    resetFlyingObject(
                        object
                    );
                }

                /*
                 * Keep the trail glued
                 * behind the shape,
                 * unaffected by its spin.
                 */
                if (
                    object.userData.trail
                ) {
                    object.userData.trail.position.set(
                        object.position.x,
                        object.position.y,
                        object.position.z -
                            (
                                object.userData
                                    .trailHalf +
                                0.3
                            )
                    );
                }
            }
        );
    }

    /* ============================================================
       GATE - the camera flies straight through this ring, and
       the show changes to its next scene the moment it happens.
       ============================================================ */

    function spawnGateRing() {
        if (
            gateRing
        ) {
            return;
        }

        const next =
            SCENES[
                (
                    sceneMode +
                    1
                ) %
                SCENES.length
            ];

        const ring =
            new THREE.Mesh(
                new THREE.TorusGeometry(
                    isMobile()
                        ? 4.4
                        : 6.2,
                    0.16,
                    12,
                    64
                ),
                new THREE.MeshBasicMaterial(
                    {
                        color:
                            next
                                .colors[0],
                        transparent: true,
                        opacity: 0.85,
                        blending:
                            THREE.AdditiveBlending,
                        side: THREE.DoubleSide
                    }
                )
            );

        ring.position.set(
            0,
            CONFIG.camera
                .desktopY,
            -70
        );

        ring.userData.travelTime =
            4.6;

        ring.userData.elapsedTravel =
            0;

        ring.userData.startZ =
            -70;

        ring.userData.endZ =
            30;

        scene.add(
            ring
        );

        gateRing =
            ring;
    }

    function applyScene(
        index
    ) {
        sceneMode =
            index %
            SCENES.length;

        const active =
            SCENES[
                sceneMode
            ];

        if (
            scene &&
            scene.fog
        ) {
            scene.fog.color.setHex(
                active.fog
            );
        }

        if (
            particleField
        ) {
            particleField.material.color.setHex(
                active
                    .colors[0]
            );
        }
    }

    /* ============================================================
       BRAND FLASH
       ============================================================ */

    function triggerBrandFlash() {
        if (
            !brandElement
        ) {
            return;
        }

        if (
            brandHideTimeout
        ) {
            clearTimeout(
                brandHideTimeout
            );

            brandHideTimeout =
                null;
        }

        /*
         * Never repeat the same
         * animation twice in a row.
         */
        let choice =
            randomChoice(
                BRAND_ANIMATIONS
            );

        if (
            BRAND_ANIMATIONS.length >
                1 &&
            choice ===
                lastBrandAnimation
        ) {
            choice =
                BRAND_ANIMATIONS[
                    (
                        BRAND_ANIMATIONS.indexOf(
                            choice
                        ) +
                        1
                    ) %
                    BRAND_ANIMATIONS.length
                ];
        }

        lastBrandAnimation =
            choice;

        brandElement.className =
            "visualizer-brand";

        /*
         * Force reflow so re-adding the
         * same class after removing it
         * restarts the CSS animation.
         */
        void brandElement.offsetWidth;

        brandElement.classList.add(
            "show",
            choice
        );

        brandHideTimeout =
            setTimeout(
                () => {
                    brandElement.classList.remove(
                        "show",
                        choice
                    );

                    brandHideTimeout =
                        null;
                },
                BRAND_ANIMATION_DURATIONS[
                    choice
                ] ||
                    3200
            );
    }

    function updateGateRing(
        delta
    ) {
        if (
            !gateRing
        ) {
            return;
        }

        gateRing.userData.elapsedTravel +=
            delta;

        const progress =
            clamp(
                gateRing.userData
                    .elapsedTravel /
                    gateRing.userData
                        .travelTime,
                0,
                1
            );

        gateRing.position.z =
            lerp(
                gateRing.userData
                    .startZ,
                gateRing.userData
                    .endZ,
                progress
            );

        gateRing.rotation.z +=
            delta *
            0.4;

        const scaleUp =
            1 +
            progress *
                0.6;

        gateRing.scale.setScalar(
            scaleUp
        );

        if (
            progress >=
            1
        ) {
            /*
             * Passed through - flash,
             * burst, advance the scene.
             */
            gateFlash =
                1;

            spawnShockwave();
            spawnShockwave();

            applyScene(
                sceneMode +
                    1
            );

            scene.remove(
                gateRing
            );

            gateRing =
                null;

            nextGateAt +=
                random(
                    9,
                    13
                );
        }
    }

    /* ============================================================
       SHOCKWAVES
       ============================================================ */

    function spawnShockwave() {
        if (
            shockwaves.length >=
            9
        ) {
            return;
        }

        const ring =
            new THREE.Mesh(
                new THREE.TorusGeometry(
                    0.50,
                    0.017,
                    8,
                    64
                ),
                new THREE.MeshBasicMaterial({
                    color:
                        CONFIG.colors[
                            (
                                groupRound +
                                currentFormation
                            ) %
                            CONFIG.colors
                                .length
                        ],

                    transparent:
                        true,

                    opacity:
                        0.42,

                    blending:
                        THREE.AdditiveBlending
                })
            );

        ring.position.set(
            random(
                -3.0,
                3.0
            ),
            random(
                2.3,
                6.7
            ),
            random(
                -2,
                1
            )
        );

        ring.rotation.y =
            Math.PI / 2;

        ring.userData.life =
            1;

        ring.userData.speed =
            random(
                7,
                10
            );

        scene.add(
            ring
        );

        shockwaves.push(
            ring
        );
    }

    function updateShockwaves(
        delta
    ) {
        for (
            let i =
                shockwaves.length -
                1;
            i >= 0;
            i--
        ) {
            const ring =
                shockwaves[i];

            ring.userData.life -=
                delta *
                0.78;

            ring.position.z +=
                ring.userData.speed *
                delta;

            ring.scale.multiplyScalar(
                1 +
                    delta *
                        (
                            2.4 +
                            overallEnergy *
                                1.8
                        )
            );

            ring.material.opacity =
                Math.max(
                    0,
                    ring.userData.life *
                        0.44
                );

            if (
                ring.userData.life <=
                    0 ||
                ring.position.z >
                    25
            ) {
                scene.remove(
                    ring
                );

                ring.geometry.dispose();

                ring.material.dispose();

                shockwaves.splice(
                    i,
                    1
                );
            }
        }
    }

    /* ============================================================
       STAGE
       ============================================================ */

    function createStage() {
        stage =
            new THREE.Group();

        scene.add(
            stage
        );

        /*
         * Dark stage.
         */
        const floor =
            new THREE.Mesh(
                new THREE.CylinderGeometry(
                    21,
                    21,
                    0.25,
                    96
                ),
                new THREE.MeshStandardMaterial({
                    color:
                        0x080a10,

                    roughness:
                        0.88,

                    metalness:
                        0.04,

                    emissive:
                        0x000000,

                    emissiveIntensity:
                        0
                })
            );

        floor.position.y =
            -0.17;

        stage.add(
            floor
        );

        /*
         * Floor rings.
         * They glow, not people.
         */
        for (
            let i = 0;
            i < 5;
            i++
        ) {
            const ring =
                new THREE.Mesh(
                    new THREE.TorusGeometry(
                        3 +
                            i *
                                2.65,
                        0.020 +
                            i *
                                0.004,
                        8,
                        96
                    ),
                    new THREE.MeshBasicMaterial({
                        color:
                            CONFIG.colors[
                                i %
                                    CONFIG
                                        .colors
                                        .length
                            ],

                        transparent:
                            true,

                        opacity:
                            0.12 -
                            i *
                                0.012,

                        blending:
                            THREE.AdditiveBlending
                    })
                );

            ring.rotation.x =
                Math.PI / 2;

            ring.position.y =
                -0.015;

            stage.add(
                ring
            );
        }

        /*
         * Background.
         */
        const backdrop =
            new THREE.Mesh(
                new THREE.PlaneGeometry(
                    110,
                    64
                ),
                new THREE.MeshBasicMaterial({
                    color:
                        0x010104
                })
            );

        backdrop.position.set(
            0,
            15,
            -19
        );

        stage.add(
            backdrop
        );

        /*
         * Vertical background light bars.
         */
        for (
            let i = -7;
            i <= 7;
            i++
        ) {
            const bar =
                new THREE.Mesh(
                    new THREE.BoxGeometry(
                        0.025,
                        random(
                            7,
                            12
                        ),
                        0.025
                    ),
                    new THREE.MeshBasicMaterial({
                        color:
                            CONFIG.colors[
                                Math.abs(
                                    i
                                ) %
                                    CONFIG.colors
                                        .length
                            ],

                        transparent:
                            true,

                        opacity:
                            0.13,

                        blending:
                            THREE.AdditiveBlending
                    })
                );

            bar.position.set(
                i *
                    2.35,
                5.2,
                -14
            );

            stage.add(
                bar
            );
        }

        /*
         * Back rings.
         */
        for (
            let i = 0;
            i < 5;
            i++
        ) {
            const ring =
                new THREE.Mesh(
                    new THREE.TorusGeometry(
                        6 +
                            i *
                                3.1,
                        0.025,
                        8,
                        96
                    ),
                    new THREE.MeshBasicMaterial({
                        color:
                            CONFIG.colors[
                                (
                                    i +
                                    2
                                ) %
                                    CONFIG
                                        .colors
                                        .length
                            ],

                        transparent:
                            true,

                        opacity:
                            0.08,

                        blending:
                            THREE.AdditiveBlending
                    })
                );

            ring.position.set(
                0,
                8,
                -13 -
                    i *
                        1.35
            );

            ring.rotation.x =
                Math.PI / 2;

            stage.add(
                ring
            );
        }

        stageLights =
            createLighting();
    }

    /* ============================================================
       LIGHTING
       ============================================================ */

    function createLighting() {
        /*
         * MUCH LOWER ambient.
         * This preserves human shape.
         */
        const ambient =
            new THREE.AmbientLight(
                0x565968,
                0.48
            );

        scene.add(
            ambient
        );

        /*
         * Soft cool front.
         */
        const front =
            new THREE.DirectionalLight(
                0xaeb8cc,
                0.42
            );

        front.position.set(
            0,
            10,
            17
        );

        scene.add(
            front
        );

        /*
         * Cyan side.
         */
        const left =
            new THREE.PointLight(
                0x2acbff,
                5.5,
                34
            );

        left.position.set(
            -13,
            7,
            8
        );

        scene.add(
            left
        );

        /*
         * Pink side.
         */
        const right =
            new THREE.PointLight(
                0xff3d86,
                5.5,
                34
            );

        right.position.set(
            13,
            7,
            8
        );

        scene.add(
            right
        );

        /*
         * Purple back rim.
         */
        const rim =
            new THREE.PointLight(
                0x735cff,
                8,
                42
            );

        rim.position.set(
            0,
            10,
            -15
        );

        scene.add(
            rim
        );

        /*
         * Tiny top separation.
         */
        const top =
            new THREE.PointLight(
                0x9eb2d4,
                1.4,
                28
            );

        top.position.set(
            0,
            14,
            3
        );

        scene.add(
            top
        );

        return {
            ambient,
            front,
            left,
            right,
            rim,
            top
        };
    }

    function updateStage(
        elapsed
    ) {
        if (!stage) {
            return;
        }

        stage.children.forEach(
            (
                object,
                index
            ) => {
                if (
                    object.geometry &&
                    object.geometry.type ===
                        "TorusGeometry"
                ) {
                    object.rotation.z =
                        Math.sin(
                            elapsed *
                                0.10 +
                                index
                        ) *
                        0.025;

                    object.scale.setScalar(
                        1 +
                            overallEnergy *
                                0.015 +
                            beatPulse *
                                0.025
                    );
                }
            }
        );

        if (
            stageLights
        ) {
            /*
             * Keep all lights low.
             */
            stageLights.front.intensity =
                0.40 +
                overallEnergy *
                    0.10;

            stageLights.left.intensity =
                3 +
                bassEnergy *
                    4 +
                beatPulse *
                    2;

            stageLights.right.intensity =
                3 +
                midEnergy *
                    4 +
                beatPulse *
                    2;

            stageLights.rim.intensity =
                4 +
                highEnergy *
                    5 +
                beatPulse *
                    2.5;

            stageLights.top.intensity =
                1.2 +
                overallEnergy *
                    1.0;
        }
    }

    /* ============================================================
       CAMERA
       ============================================================ */

    function updateCamera(
        delta,
        elapsed
    ) {
        if (!camera) {
            return;
        }

        smoothMouseX =
            lerp(
                smoothMouseX,
                mouseX,
                0.045
            );

        smoothMouseY =
            lerp(
                smoothMouseY,
                mouseY,
                0.045
            );

        const mobile =
            isMobile();

        /*
         * The camera itself moves enough
         * to reveal depth, but doesn't lose
         * the performers.
         */
        const performanceBoost =
            performanceMode ===
            "group"
                ? 1.15
                : performanceMode ===
                  "solo"
                    ? 0.30
                    : 0.70;

        /*
         * Spotlight: push in close
         * on the featured dancer.
         */
        const soloZoom =
            performanceMode ===
            "solo"
                ? mobile
                    ? 5.5
                    : 7.0
                : 0;

        const orbit =
            elapsed *
            0.105;

        const orbitX =
            Math.sin(
                orbit
            ) *
            (
                mobile
                    ? 1.35
                    : 2.25
            ) *
            performanceBoost;

        const targetX =
            orbitX +
            smoothMouseX *
                2.2;

        const targetY =
            (
                mobile
                    ? CONFIG.camera
                          .mobileY
                    : CONFIG.camera
                          .desktopY
            ) +
            Math.sin(
                elapsed *
                    0.30
            ) *
                0.18 +
            smoothMouseY *
                0.50;

        const baseZ =
            mobile
                ? CONFIG.camera
                      .mobileZ
                : CONFIG.camera
                      .desktopZ;

        /*
         * Beat push.
         */
        const targetZ =
            baseZ -
            beatPulse *
                0.75 +
            Math.sin(
                elapsed *
                    0.16
            ) *
                0.65 -
            soloZoom;

        camera.position.x =
            damp(
                camera.position.x,
                targetX,
                CONFIG.camera
                    .smoothing,
                delta
            );

        camera.position.y =
            damp(
                camera.position.y,
                targetY,
                CONFIG.camera
                    .smoothing,
                delta
            );

        camera.position.z =
            damp(
                camera.position.z,
                targetZ,
                CONFIG.camera
                    .smoothing,
                delta
            );

        /*
         * Track the whole formation.
         */
        const lookX =
            smoothMouseX *
            0.65;

        const lookY =
            5.0 +
            smoothMouseY *
                0.45;

        camera.lookAt(
            lookX,
            lookY,
            0
        );

        camera.rotation.z =
            damp(
                camera.rotation.z,
                smoothMouseX *
                    0.006,
                2.2,
                delta
            );
    }

    /* ============================================================
       BLOOM
       ============================================================ */

    function updateBloom() {
        if (!bloomPass) {
            return;
        }

        /*
         * No performers on screen now -
         * push the glow much harder for a
         * premium, attention-grabbing look.
         * Each scene has its own glow
         * personality, and passing through
         * a gate spikes it briefly.
         */
        bloomPass.strength =
            SCENES[
                sceneMode
            ].bloom +
            overallEnergy *
                0.30 +
            beatPulse *
                0.40 +
            gateFlash *
                1.1;

        bloomPass.radius =
            0.36;

        bloomPass.threshold =
            0.30;
    }

    /* ============================================================
       LYRICS
       ============================================================ */

    function initLyrics() {
        if (
            lyricsInitialized ||
            !lyricsElement
        ) {
            return;
        }

        const source =
            window.lyricsSegments ||
            window.LYRICS_SEGMENTS ||
            [];

        if (
            !Array.isArray(
                source
            ) ||
            !source.length
        ) {
            return;
        }

        lyricsData =
            source
                .map(
                    (
                        item,
                        index
                    ) => {
                        const start =
                            Number(
                                item.start_seconds ??
                                    item.startTime ??
                                    index *
                                        4
                            );

                        const end =
                            Number(
                                item.end_seconds ??
                                    item.endTime ??
                                    start +
                                        4
                            );

                        return {
                            text:
                                item.text ||
                                item.lyrics ||
                                "",

                            start,

                            end
                        };
                    }
                )
                .filter(
                    item =>
                        item.text
                );

        lyricsInitialized =
            true;
    }

    /* ============================================================
       PROGRESS BAR
       ============================================================ */

    function formatVisualizerTime(
        seconds
    ) {
        if (
            !seconds ||
            isNaN(
                seconds
            )
        ) {
            return "0:00";
        }

        const mins =
            Math.floor(
                seconds /
                    60
            );

        const secs =
            Math.floor(
                seconds %
                    60
            );

        return (
            mins +
            ":" +
            (
                secs < 10
                    ? "0"
                    : ""
            ) +
            secs
        );
    }

    function updateVisualizerProgress() {
        if (
            !progressFill ||
            !window.globalAudio ||
            !window.globalAudio
                .duration
        ) {
            return;
        }

        const percent =
            clamp(
                (
                    window.globalAudio
                        .currentTime /
                    window.globalAudio
                        .duration
                ) *
                    100,
                0,
                100
            );

        progressFill.style.width =
            percent +
            "%";

        if (
            progressCurrentEl
        ) {
            progressCurrentEl.textContent =
                formatVisualizerTime(
                    window.globalAudio
                        .currentTime
                );
        }

        if (
            progressDurationEl
        ) {
            progressDurationEl.textContent =
                formatVisualizerTime(
                    window.globalAudio
                        .duration
                );
        }
    }

    let isDraggingVisualizerProgress =
        false;

    function seekVisualizerProgress(
        clientX
    ) {
        if (
            !progressTrack ||
            !window.globalAudio ||
            !window.globalAudio
                .duration
        ) {
            return;
        }

        const rect =
            progressTrack.getBoundingClientRect();

        /*
         * The fill is positioned with
         * inset-inline-start, so in RTL
         * it visually grows from the
         * right edge - measure from
         * whichever edge is actually the
         * logical start, or a click
         * lands on the mirrored point.
         */
        const isRtl =
            getComputedStyle(
                progressTrack
            ).direction ===
            "rtl";

        const ratio =
            isRtl
                ? clamp(
                      (
                          rect.right -
                          clientX
                      ) /
                          rect.width,
                      0,
                      1
                  )
                : clamp(
                      (
                          clientX -
                          rect.left
                      ) /
                          rect.width,
                      0,
                      1
                  );

        window.globalAudio.currentTime =
            ratio *
            window.globalAudio
                .duration;

        updateVisualizerProgress();
    }

    if (
        progressTrack
    ) {
        progressTrack.addEventListener(
            "pointerdown",
            event => {
                isDraggingVisualizerProgress =
                    true;

                progressTrack.setPointerCapture(
                    event.pointerId
                );

                seekVisualizerProgress(
                    event.clientX
                );
            }
        );

        progressTrack.addEventListener(
            "pointermove",
            event => {
                if (
                    isDraggingVisualizerProgress
                ) {
                    seekVisualizerProgress(
                        event.clientX
                    );
                }
            }
        );

        progressTrack.addEventListener(
            "pointerup",
            () => {
                isDraggingVisualizerProgress =
                    false;
            }
        );

        progressTrack.addEventListener(
            "pointercancel",
            () => {
                isDraggingVisualizerProgress =
                    false;
            }
        );
    }

    function updateLyrics() {
        if (
            !lyricsInitialized ||
            !lyricsElement ||
            !window.globalAudio
        ) {
            return;
        }

        const currentTime =
            Number(
                window.globalAudio
                    .currentTime
            );

        let active =
            -1;

        for (
            let i = 0;
            i <
            lyricsData.length;
            i++
        ) {
            const item =
                lyricsData[i];

            if (
                currentTime >=
                    item.start &&
                currentTime <
                    item.end
            ) {
                active =
                    i;

                break;
            }
        }

        if (
            active !== -1 &&
            active !==
                lastLyricIndex
        ) {
            lastLyricIndex =
                active;

            lyricsElement.style.opacity =
                "0";

            setTimeout(
                () => {
                    if (
                        lyricsElement
                    ) {
                        lyricsElement.textContent =
                            lyricsData[
                                active
                            ].text;

                        lyricsElement.style.opacity =
                            "1";
                    }
                },
                80
            );
        }
    }

    /* ============================================================
       POINTER
       ============================================================ */

    function onPointerMove(
        event
    ) {
        mouseX =
            (
                event.clientX /
                    window.innerWidth -
                0.5
            ) *
            2;

        mouseY =
            (
                event.clientY /
                    window.innerHeight -
                0.5
            ) *
            2;
    }

    /* ============================================================
       RESIZE
       ============================================================ */

    function onResize() {
        if (
            !camera ||
            !renderer
        ) {
            return;
        }

        const width =
            window.innerWidth;

        const height =
            Math.max(
                1,
                window.innerHeight
            );

        camera.aspect =
            width /
            height;

        camera.updateProjectionMatrix();

        renderer.setPixelRatio(
            Math.min(
                window.devicePixelRatio ||
                    1,
                isMobile()
                    ? CONFIG.mobile
                          .pixelRatio
                    : CONFIG.desktop
                          .pixelRatio
            )
        );

        renderer.setSize(
            width,
            height,
            false
        );

        if (
            composer
        ) {
            composer.setSize(
                width,
                height
            );
        }

        if (
            bloomPass
        ) {
            bloomPass.resolution.set(
                width,
                height
            );
        }
    }

    /* ============================================================
       THREE INITIALIZATION
       ============================================================ */

    function initThree() {
        const mobile =
            isMobile();

        scene =
            new THREE.Scene();

        scene.background =
            new THREE.Color(
                0x020207
            );

        scene.fog =
            new THREE.FogExp2(
                0x020207,
                mobile
                    ? 0.007
                    : 0.0045
            );

        camera =
            new THREE.PerspectiveCamera(
                CONFIG.camera.fov,
                window.innerWidth /
                    Math.max(
                        1,
                        window.innerHeight
                    ),
                0.05,
                300
            );

        camera.position.set(
            0,
            mobile
                ? CONFIG.camera
                      .mobileY
                : CONFIG.camera
                      .desktopY,
            mobile
                ? CONFIG.camera
                      .mobileZ
                : CONFIG.camera
                      .desktopZ
        );

        camera.lookAt(
            0,
            5,
            0
        );

        renderer =
            new THREE.WebGLRenderer({
                canvas,

                antialias:
                    !mobile,

                alpha: true,

                powerPreference:
                    "high-performance"
            });

        renderer.setPixelRatio(
            Math.min(
                window.devicePixelRatio ||
                    1,
                mobile
                    ? CONFIG.mobile
                          .pixelRatio
                    : CONFIG.desktop
                          .pixelRatio
            )
        );

        renderer.setSize(
            window.innerWidth,
            window.innerHeight,
            false
        );

        if (
            "outputColorSpace" in
                renderer &&
            THREE.SRGBColorSpace
        ) {
            renderer.outputColorSpace =
                THREE.SRGBColorSpace;
        }

        renderer.toneMapping =
            THREE.ACESFilmicToneMapping;

        /*
         * Deliberately low.
         */
        renderer.toneMappingExposure =
            0.82;

        canvas.style.position =
            "absolute";

        canvas.style.left =
            "0";

        canvas.style.top =
            "0";

        canvas.style.width =
            "100%";

        canvas.style.height =
            "100%";

        canvas.style.display =
            "block";

        setupComposer();
    }

    /* ============================================================
       COMPOSER
       ============================================================ */

    function setupComposer() {
        const Composer =
            THREE.EffectComposer ||
            window.EffectComposer;

        const RenderPass =
            THREE.RenderPass ||
            window.RenderPass;

        const UnrealBloomPass =
            THREE.UnrealBloomPass ||
            window.UnrealBloomPass;

        if (
            !Composer ||
            !RenderPass ||
            !UnrealBloomPass
        ) {
            composer = null;

            bloomPass = null;

            return;
        }

        try {
            composer =
                new Composer(
                    renderer
                );

            composer.addPass(
                new RenderPass(
                    scene,
                    camera
                )
            );

            bloomPass =
                new UnrealBloomPass(
                    new THREE.Vector2(
                        window.innerWidth,
                        window.innerHeight
                    ),
                    0.20,
                    0.28,
                    0.38
                );

            composer.addPass(
                bloomPass
            );

        } catch (error) {
            composer = null;
            bloomPass = null;

            console.warn(
                "[Visualizer] Bloom unavailable:",
                error
            );
        }
    }

    /* ============================================================
       ANIMATION
       ============================================================ */

    function animate() {
        if (
            !visualizerVisible
        ) {
            animationId =
                null;

            return;
        }

        animationId =
            requestAnimationFrame(
                animate
            );

        const delta =
            Math.min(
                clock.getDelta(),
                0.05
            );

        const elapsed =
            clock.elapsedTime;

        updateAudio(
            delta
        );

        updatePerformance(
            delta,
            elapsed
        );

        updateParticleField(
            delta,
            elapsed
        );

        updateFlyingObjects(
            delta,
            elapsed
        );

        updateShockwaves(
            delta
        );

        /*
         * Periodic gate the camera
         * flies through - marks the
         * transition to the next scene.
         */
        if (
            !gateRing &&
            elapsed >=
                nextGateAt
        ) {
            spawnGateRing();
        }

        updateGateRing(
            delta
        );

        if (
            gateFlash >
            0
        ) {
            gateFlash =
                Math.max(
                    0,
                    gateFlash -
                        delta *
                            2.2
                );
        }

        /*
         * "Tamer Hosny" brand flash -
         * a different animation every
         * time it appears.
         */
        if (
            elapsed >=
            nextBrandAt
        ) {
            triggerBrandFlash();

            nextBrandAt =
                elapsed +
                random(
                    11,
                    17
                );
        }

        updateStage(
            elapsed
        );

        updateCamera(
            delta,
            elapsed
        );

        updateBloom();

        updateLyrics();

        if (
            !isDraggingVisualizerProgress
        ) {
            updateVisualizerProgress();
        }

        /*
         * Beat event.
         */
        if (
            beatPulse >
                0.62 &&
            elapsed -
                lastBeatSpawnTime >
                0.14
        ) {
            spawnShockwave();

            lastBeatSpawnTime =
                elapsed;
        }

        if (
            composer
        ) {
            composer.render();

        } else if (
            renderer &&
            scene &&
            camera
        ) {
            renderer.render(
                scene,
                camera
            );
        }
    }

    /* ============================================================
       INITIALIZATION
       ============================================================ */

    function initVisualizer() {
        if (
            visualizerInitialized
        ) {
            return;
        }

        if (
            typeof THREE ===
            "undefined"
        ) {
            console.error(
                "[Visualizer] THREE.js is not loaded."
            );

            return;
        }

        clock =
            new THREE.Clock();

        initThree();

        createStage();

        createParticleField();

        createFlyingObjects();

        createDancers();

        initLyrics();

        window.addEventListener(
            "resize",
            onResize,
            {
                passive: true
            }
        );

        window.addEventListener(
            "pointermove",
            onPointerMove,
            {
                passive: true
            }
        );

        onResize();

        visualizerInitialized =
            true;

        console.log(
            "[Visualizer] PERFORMANCE ENGINE READY",
            {
                dancers:
                    dancers.length,

                mode:
                    performanceMode,

                formation:
                    FORMATIONS[
                        currentFormation
                    ]
            }
        );
    }

    /* ============================================================
       VISIBILITY
       ============================================================ */

    function forceVisible() {
        if (
            container.parentElement !==
            document.body
        ) {
            document.body.appendChild(
                container
            );
        }

        /*
         * No width/height (100vw/100vh are unreliable on
         * mobile - address-bar toolbars, RTL layout, any
         * stray horizontal overflow elsewhere on the page
         * can all throw them off, leaving a gap with the
         * page behind visible). `inset: 0` on a `position:
         * fixed` element always fills exactly what's on
         * screen instead.
         */
        const styles = {
            display: "block",
            visibility: "visible",
            opacity: "1",
            "pointer-events": "auto",
            position: "fixed",
            inset: "0",
            margin: "0",
            padding: "0",
            overflow: "hidden",
            "z-index": "999999",
            background: "#020207"
        };

        Object.keys(
            styles
        ).forEach(
            key => {
                container.style.setProperty(
                    key,
                    styles[key],
                    "important"
                );
            }
        );

        canvas.style.setProperty(
            "display",
            "block",
            "important"
        );

        canvas.style.setProperty(
            "visibility",
            "visible",
            "important"
        );

        canvas.style.setProperty(
            "opacity",
            "1",
            "important"
        );

        canvas.style.setProperty(
            "width",
            "100%",
            "important"
        );

        canvas.style.setProperty(
            "height",
            "100%",
            "important"
        );
    }

    /* ============================================================
       SHOW
       ============================================================ */

    function showVisualizer() {
        if (
            visualizerVisible
        ) {
            return;
        }

        if (
            container._hideTimeout
        ) {
            clearTimeout(
                container._hideTimeout
            );

            container._hideTimeout =
                null;
        }

        try {
            forceVisible();

            initVisualizer();

            initAudio();

        } catch (error) {
            console.error(
                "[Visualizer] Startup failed:",
                error
            );

            console.error(
                error.stack
            );

            return;
        }

        visualizerVisible =
            true;

        container.classList.add(
            "active"
        );

        forceVisible();

        /*
         * Lock the page behind the
         * fullscreen overlay - otherwise
         * mobile browsers still let the
         * page scroll/bounce underneath.
         */
        document.documentElement.style.setProperty(
            "overflow",
            "hidden",
            "important"
        );

        document.body.style.setProperty(
            "overflow",
            "hidden",
            "important"
        );

        requestAnimationFrame(
            () => {
                onResize();

                if (
                    camera
                ) {
                    camera.position.set(
                        0,
                        isMobile()
                            ? CONFIG
                                  .camera
                                  .mobileY
                            : CONFIG
                                  .camera
                                  .desktopY,

                        isMobile()
                            ? CONFIG
                                  .camera
                                  .mobileZ
                            : CONFIG
                                  .camera
                                  .desktopZ
                    );

                    camera.lookAt(
                        0,
                        5,
                        0
                    );
                }
            }
        );

        if (
            audioContext &&
            audioContext.state ===
                "suspended"
        ) {
            audioContext
                .resume()
                .catch(
                    () => {}
                );
        }

        if (
            !animationId
        ) {
            clock.start();

            animate();
        }

        if (
            toggleButton
        ) {
            toggleButton.classList.add(
                "active"
            );
        }

        console.log(
            "[Visualizer] OPENED"
        );
    }

    /* ============================================================
       HIDE
       ============================================================ */

    function hideVisualizer() {
        if (
            !visualizerVisible
        ) {
            return;
        }

        visualizerVisible =
            false;

        if (
            animationId
        ) {
            cancelAnimationFrame(
                animationId
            );

            animationId =
                null;
        }

        document.documentElement.style.removeProperty(
            "overflow"
        );

        document.body.style.removeProperty(
            "overflow"
        );

        if (
            brandHideTimeout
        ) {
            clearTimeout(
                brandHideTimeout
            );

            brandHideTimeout =
                null;
        }

        if (
            brandElement
        ) {
            brandElement.className =
                "visualizer-brand";
        }

        nextBrandAt =
            5;

        if (
            toggleButton
        ) {
            toggleButton.classList.remove(
                "active"
            );
        }

        container.classList.remove(
            "active"
        );

        container.style.setProperty(
            "opacity",
            "0",
            "important"
        );

        container.style.setProperty(
            "pointer-events",
            "none",
            "important"
        );

        container._hideTimeout =
            setTimeout(
                () => {
                    if (
                        !visualizerVisible
                    ) {
                        container.style.setProperty(
                            "display",
                            "none",
                            "important"
                        );
                    }
                },
                260
            );

        console.log(
            "[Visualizer] CLOSED"
        );
    }

    /* ============================================================
       GLOBAL TOGGLE
       ============================================================ */

    /*
     * HTML should keep:
     *
     * onclick="toggle3DVisualizer()"
     *
     * Do not add another click handler.
     */

    window.toggle3DVisualizer =
        function () {
            if (
                visualizerVisible
            ) {
                hideVisualizer();

            } else {
                showVisualizer();
            }
        };

    /* ============================================================
       CLEANUP
       ============================================================ */

    window.destroy3DVisualizer =
        function () {
            visualizerVisible =
                false;

            if (
                animationId
            ) {
                cancelAnimationFrame(
                    animationId
                );

                animationId =
                    null;
            }

            window.removeEventListener(
                "resize",
                onResize
            );

            window.removeEventListener(
                "pointermove",
                onPointerMove
            );

            if (
                scene
            ) {
                scene.traverse(
                    object => {
                        if (
                            object.geometry
                        ) {
                            object.geometry.dispose();
                        }

                        if (
                            object.material
                        ) {
                            if (
                                Array.isArray(
                                    object.material
                                )
                            ) {
                                object.material.forEach(
                                    material => {
                                        if (
                                            material &&
                                            material.dispose
                                        ) {
                                            material.dispose();
                                        }
                                    }
                                );
                            } else if (
                                object.material.dispose
                            ) {
                                object.material.dispose();
                            }
                        }
                    }
                );
            }

            if (
                renderer
            ) {
                renderer.dispose();
            }

            if (
                composer &&
                composer.dispose
            ) {
                composer.dispose();
            }

            scene = null;
            camera = null;
            renderer = null;
            composer = null;
            bloomPass = null;

            clock = null;

            stage = null;
            stageLights = null;

            particleField = null;
            particleData = null;

            dancers = [];
            flyingObjects = [];
            shockwaves = [];

            gateRing = null;
            sceneMode = 0;
            nextGateAt = 6.5;
            gateFlash = 0;

            lyricsData = [];
            lyricsInitialized =
                false;
            lastLyricIndex =
                -1;

            visualizerInitialized =
                false;

            performanceMode =
                "individual";

            performanceTimer =
                0;

            currentFormation =
                0;

            groupRound =
                0;

            individualRound =
                0;

            console.log(
                "[Visualizer] DESTROYED"
            );
        };

    /* ============================================================
       KEYBOARD
       ============================================================ */

    document.addEventListener(
        "keydown",
        event => {
            const tag =
                event.target?.tagName;

            if (
                tag === "INPUT" ||
                tag === "TEXTAREA" ||
                tag === "SELECT" ||
                event.target?.isContentEditable
            ) {
                return;
            }

            if (
                event.key.toLowerCase() ===
                "v"
            ) {
                window.toggle3DVisualizer();
            }

            if (
                event.key ===
                    "Escape" &&
                visualizerVisible
            ) {
                hideVisualizer();
            }
        }
    );

    /* ============================================================
       DEBUG API
       ============================================================ */

    window.__tamerVisualizer = {
        get scene() {
            return scene;
        },

        get camera() {
            return camera;
        },

        get dancers() {
            return dancers;
        },

        get mode() {
            return performanceMode;
        },

        get formation() {
            return FORMATIONS[
                currentFormation
            ];
        },

        get groupMove() {
            return GROUP_MOVES[
                groupRound %
                    GROUP_MOVES.length
            ];
        },

        get energy() {
            return {
                bass:
                    bassEnergy,

                mid:
                    midEnergy,

                high:
                    highEnergy,

                overall:
                    overallEnergy,

                beat:
                    beatPulse
            };
        },

        get effects() {
            return {
                flying:
                    flyingObjects.length,

                shockwaves:
                    shockwaves.length
            };
        },

        get initialized() {
            return visualizerInitialized;
        },

        get visible() {
            return visualizerVisible;
        }
    };

    /* ============================================================
       READY
       ============================================================ */

    console.log(
        "%c Tamer Hosny - Immersive Dance Performance Engine Loaded ",
        "background:#04040b;color:#36e5ff;font-weight:bold;padding:9px 15px;border-radius:8px;"
    );

})();