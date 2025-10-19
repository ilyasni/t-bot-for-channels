--
-- PostgreSQL database dump
--

\restrict Th7E8WFrZMZfB8H0IXUbZEm49bcGRtkauZ737knI2Qc1k8tbFvCG7P15vDeOWae

-- Dumped from database version 18.0 (Debian 18.0-1.pgdg13+3)
-- Dumped by pg_dump version 18.0 (Debian 18.0-1.pgdg13+3)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY "public"."evaluation_results" DROP CONSTRAINT IF EXISTS "evaluation_results_run_id_fkey";
DROP TRIGGER IF EXISTS "update_golden_dataset_updated_at" ON "public"."evaluation_golden_dataset";
DROP INDEX IF EXISTS "public"."idx_golden_dataset_name";
DROP INDEX IF EXISTS "public"."idx_golden_dataset_difficulty";
DROP INDEX IF EXISTS "public"."idx_golden_dataset_created_at";
DROP INDEX IF EXISTS "public"."idx_golden_dataset_category";
DROP INDEX IF EXISTS "public"."idx_evaluation_runs_status";
DROP INDEX IF EXISTS "public"."idx_evaluation_runs_started_at";
DROP INDEX IF EXISTS "public"."idx_evaluation_runs_provider";
DROP INDEX IF EXISTS "public"."idx_evaluation_runs_name";
DROP INDEX IF EXISTS "public"."idx_evaluation_runs_dataset";
DROP INDEX IF EXISTS "public"."idx_evaluation_runs_created_at";
DROP INDEX IF EXISTS "public"."idx_evaluation_results_run_id";
DROP INDEX IF EXISTS "public"."idx_evaluation_results_overall_score";
DROP INDEX IF EXISTS "public"."idx_evaluation_results_item_id";
DROP INDEX IF EXISTS "public"."idx_evaluation_results_evaluated_at";
ALTER TABLE IF EXISTS ONLY "public"."evaluation_runs" DROP CONSTRAINT IF EXISTS "evaluation_runs_run_name_key";
ALTER TABLE IF EXISTS ONLY "public"."evaluation_runs" DROP CONSTRAINT IF EXISTS "evaluation_runs_pkey";
ALTER TABLE IF EXISTS ONLY "public"."evaluation_results" DROP CONSTRAINT IF EXISTS "evaluation_results_pkey";
ALTER TABLE IF EXISTS ONLY "public"."evaluation_golden_dataset" DROP CONSTRAINT IF EXISTS "evaluation_golden_dataset_pkey";
ALTER TABLE IF EXISTS ONLY "public"."evaluation_golden_dataset" DROP CONSTRAINT IF EXISTS "evaluation_golden_dataset_item_id_key";
ALTER TABLE IF EXISTS "public"."evaluation_runs" ALTER COLUMN "id" DROP DEFAULT;
ALTER TABLE IF EXISTS "public"."evaluation_results" ALTER COLUMN "id" DROP DEFAULT;
ALTER TABLE IF EXISTS "public"."evaluation_golden_dataset" ALTER COLUMN "id" DROP DEFAULT;
DROP SEQUENCE IF EXISTS "public"."evaluation_runs_id_seq";
DROP TABLE IF EXISTS "public"."evaluation_runs";
DROP SEQUENCE IF EXISTS "public"."evaluation_results_id_seq";
DROP TABLE IF EXISTS "public"."evaluation_results";
DROP SEQUENCE IF EXISTS "public"."evaluation_golden_dataset_id_seq";
DROP TABLE IF EXISTS "public"."evaluation_golden_dataset";
DROP FUNCTION IF EXISTS "public"."update_updated_at_column"();
--
-- Name: SCHEMA "public"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA "public" IS 'standard public schema';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = "heap";

--
-- Name: evaluation_golden_dataset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE "public"."evaluation_golden_dataset" (
    "id" integer NOT NULL,
    "dataset_name" character varying(255) NOT NULL,
    "item_id" character varying(255) NOT NULL,
    "category" character varying(100) NOT NULL,
    "input_data" "jsonb" NOT NULL,
    "query" "text" NOT NULL,
    "telegram_context" "jsonb" NOT NULL,
    "expected_output" "text" NOT NULL,
    "retrieved_contexts" "jsonb",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "difficulty" character varying(20),
    "tone" character varying(20),
    "requires_multi_source" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone,
    CONSTRAINT "valid_difficulty" CHECK ((("difficulty")::"text" = ANY ((ARRAY['beginner'::character varying, 'intermediate'::character varying, 'advanced'::character varying, 'expert'::character varying])::"text"[]))),
    CONSTRAINT "valid_tone" CHECK ((("tone")::"text" = ANY ((ARRAY['technical'::character varying, 'professional'::character varying, 'casual'::character varying, 'friendly'::character varying, 'formal'::character varying])::"text"[])))
);


--
-- Name: TABLE "evaluation_golden_dataset"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE "public"."evaluation_golden_dataset" IS 'Golden dataset items for bot evaluation';


--
-- Name: COLUMN "evaluation_golden_dataset"."input_data"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN "public"."evaluation_golden_dataset"."input_data" IS 'JSON input data for bot (query, user_id, channels, etc.)';


--
-- Name: COLUMN "evaluation_golden_dataset"."telegram_context"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN "public"."evaluation_golden_dataset"."telegram_context" IS 'Telegram-specific context (channels, groups, context_type)';


--
-- Name: COLUMN "evaluation_golden_dataset"."retrieved_contexts"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN "public"."evaluation_golden_dataset"."retrieved_contexts" IS 'Retrieved contexts for RAG evaluation';


--
-- Name: evaluation_golden_dataset_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE "public"."evaluation_golden_dataset_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluation_golden_dataset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."evaluation_golden_dataset_id_seq" OWNED BY "public"."evaluation_golden_dataset"."id";


--
-- Name: evaluation_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE "public"."evaluation_results" (
    "id" integer NOT NULL,
    "run_id" integer,
    "item_id" character varying(255) NOT NULL,
    "query" "text" NOT NULL,
    "expected_output" "text" NOT NULL,
    "actual_output" "text" NOT NULL,
    "retrieved_contexts" "jsonb",
    "telegram_context" "jsonb" NOT NULL,
    "answer_correctness" double precision,
    "faithfulness" double precision,
    "context_relevance" double precision,
    "factual_correctness" double precision,
    "channel_context_awareness" double precision,
    "group_synthesis_quality" double precision,
    "multi_source_coherence" double precision,
    "tone_appropriateness" double precision,
    "overall_score" double precision,
    "evaluation_time" double precision,
    "model_used" character varying(100),
    "error_message" "text",
    "debug_info" "jsonb" DEFAULT '{}'::"jsonb",
    "evaluated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "valid_scores" CHECK (((("answer_correctness" IS NULL) OR (("answer_correctness" >= (0.0)::double precision) AND ("answer_correctness" <= (1.0)::double precision))) AND (("faithfulness" IS NULL) OR (("faithfulness" >= (0.0)::double precision) AND ("faithfulness" <= (1.0)::double precision))) AND (("context_relevance" IS NULL) OR (("context_relevance" >= (0.0)::double precision) AND ("context_relevance" <= (1.0)::double precision))) AND (("factual_correctness" IS NULL) OR (("factual_correctness" >= (0.0)::double precision) AND ("factual_correctness" <= (1.0)::double precision))) AND (("channel_context_awareness" IS NULL) OR (("channel_context_awareness" >= (0.0)::double precision) AND ("channel_context_awareness" <= (1.0)::double precision))) AND (("group_synthesis_quality" IS NULL) OR (("group_synthesis_quality" >= (0.0)::double precision) AND ("group_synthesis_quality" <= (1.0)::double precision))) AND (("multi_source_coherence" IS NULL) OR (("multi_source_coherence" >= (0.0)::double precision) AND ("multi_source_coherence" <= (1.0)::double precision))) AND (("tone_appropriateness" IS NULL) OR (("tone_appropriateness" >= (0.0)::double precision) AND ("tone_appropriateness" <= (1.0)::double precision))) AND (("overall_score" IS NULL) OR (("overall_score" >= (0.0)::double precision) AND ("overall_score" <= (1.0)::double precision)))))
);


--
-- Name: TABLE "evaluation_results"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE "public"."evaluation_results" IS 'Detailed results of individual item evaluations';


--
-- Name: COLUMN "evaluation_results"."overall_score"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN "public"."evaluation_results"."overall_score" IS 'Overall quality score (0.0-1.0)';


--
-- Name: COLUMN "evaluation_results"."debug_info"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN "public"."evaluation_results"."debug_info" IS 'JSON with debug information from evaluation';


--
-- Name: evaluation_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE "public"."evaluation_results_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluation_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."evaluation_results_id_seq" OWNED BY "public"."evaluation_results"."id";


--
-- Name: evaluation_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE "public"."evaluation_runs" (
    "id" integer NOT NULL,
    "run_name" character varying(255) NOT NULL,
    "dataset_name" character varying(255) NOT NULL,
    "model_provider" character varying(50) NOT NULL,
    "model_name" character varying(100) NOT NULL,
    "parallel_workers" integer DEFAULT 4,
    "timeout_seconds" integer DEFAULT 300,
    "status" character varying(20) DEFAULT 'pending'::character varying,
    "progress" double precision DEFAULT 0.0,
    "total_items" integer DEFAULT 0,
    "processed_items" integer DEFAULT 0,
    "successful_items" integer DEFAULT 0,
    "failed_items" integer DEFAULT 0,
    "avg_score" double precision,
    "scores" "jsonb",
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "evaluation_runs_progress_check" CHECK ((("progress" >= (0.0)::double precision) AND ("progress" <= (1.0)::double precision))),
    CONSTRAINT "valid_model_provider" CHECK ((("model_provider")::"text" = ANY ((ARRAY['gigachat'::character varying, 'openrouter'::character varying, 'openai'::character varying, 'anthropic'::character varying])::"text"[]))),
    CONSTRAINT "valid_status" CHECK ((("status")::"text" = ANY ((ARRAY['pending'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'timeout'::character varying])::"text"[])))
);


--
-- Name: TABLE "evaluation_runs"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE "public"."evaluation_runs" IS 'Evaluation runs tracking and configuration';


--
-- Name: COLUMN "evaluation_runs"."progress"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN "public"."evaluation_runs"."progress" IS 'Progress from 0.0 to 1.0';


--
-- Name: COLUMN "evaluation_runs"."scores"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN "public"."evaluation_runs"."scores" IS 'JSON with detailed scores per metric';


--
-- Name: evaluation_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE "public"."evaluation_runs_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluation_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE "public"."evaluation_runs_id_seq" OWNED BY "public"."evaluation_runs"."id";


--
-- Name: evaluation_golden_dataset id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_golden_dataset" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."evaluation_golden_dataset_id_seq"'::"regclass");


--
-- Name: evaluation_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_results" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."evaluation_results_id_seq"'::"regclass");


--
-- Name: evaluation_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_runs" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."evaluation_runs_id_seq"'::"regclass");


--
-- Data for Name: evaluation_golden_dataset; Type: TABLE DATA; Schema: public; Owner: -
--

COPY "public"."evaluation_golden_dataset" ("id", "dataset_name", "item_id", "category", "input_data", "query", "telegram_context", "expected_output", "retrieved_contexts", "metadata", "difficulty", "tone", "requires_multi_source", "created_at", "updated_at") FROM stdin;
1	sample_dataset	sample_001	automotive_tech	{"user_id": 123456, "channels": ["@drifting_channel"], "context_type": "single_channel"}	Как настроить дифференциал для дрифта?	{"user_id": 123456, "channels": ["@drifting_channel"], "context_type": "single_channel"}	Для дрифта нужно настроить LSD дифференциал с блокировкой...	\N	{"category": "automotive_tech", "requires_multi_source": false}	advanced	technical	f	2025-10-17 08:08:26.658659+00	\N
3	test_ai_dataset	test_001	ai_tech	{"user_id": 123456, "channels": ["@ai_tech_channel"], "context_type": "single_channel"}	Что такое машинное обучение?	{"channel_id": 12345, "context_type": "channel", "channel_username": "ai_tech_channel"}	Машинное обучение - это область искусственного интеллекта, которая позволяет компьютерам обучаться и принимать решения на основе данных без явного программирования.	\N	{"category": "ai_tech", "requires_multi_source": false}	intermediate	technical	f	2025-10-17 18:59:25.043436+00	\N
4	test_ai_dataset	test_002	ai_tech	{"user_id": 123456, "channels": ["@ai_tech_channel"], "context_type": "single_channel"}	Как работает нейронная сеть?	{"channel_id": 12345, "context_type": "channel", "channel_username": "ai_tech_channel"}	Нейронная сеть состоит из взаимосвязанных узлов (нейронов), которые обрабатывают информацию слоями. Каждый нейрон получает входные данные, применяет весовые коэффициенты и функцию активации, затем передает результат следующему слою.	\N	{"category": "ai_tech", "requires_multi_source": false}	advanced	technical	f	2025-10-17 18:59:30.117199+00	\N
5	test_ai_dataset	test_003	programming	{"user_id": 123456, "channels": ["@programming_channel"], "context_type": "single_channel"}	Что такое Python?	{"channel_id": 67890, "context_type": "channel", "channel_username": "programming_channel"}	Python - это высокоуровневый язык программирования общего назначения, известный своей простотой и читаемостью. Он широко используется в веб-разработке, анализе данных, машинном обучении и автоматизации.	\N	{"category": "programming", "requires_multi_source": false}	beginner	professional	f	2025-10-17 18:59:35.617332+00	\N
\.


--
-- Data for Name: evaluation_results; Type: TABLE DATA; Schema: public; Owner: -
--

COPY "public"."evaluation_results" ("id", "run_id", "item_id", "query", "expected_output", "actual_output", "retrieved_contexts", "telegram_context", "answer_correctness", "faithfulness", "context_relevance", "factual_correctness", "channel_context_awareness", "group_synthesis_quality", "multi_source_coherence", "tone_appropriateness", "overall_score", "evaluation_time", "model_used", "error_message", "debug_info", "evaluated_at") FROM stdin;
\.


--
-- Data for Name: evaluation_runs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY "public"."evaluation_runs" ("id", "run_name", "dataset_name", "model_provider", "model_name", "parallel_workers", "timeout_seconds", "status", "progress", "total_items", "processed_items", "successful_items", "failed_items", "avg_score", "scores", "started_at", "completed_at", "created_at") FROM stdin;
\.


--
-- Name: evaluation_golden_dataset_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('"public"."evaluation_golden_dataset_id_seq"', 5, true);


--
-- Name: evaluation_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('"public"."evaluation_results_id_seq"', 1, false);


--
-- Name: evaluation_runs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('"public"."evaluation_runs_id_seq"', 1, false);


--
-- Name: evaluation_golden_dataset evaluation_golden_dataset_item_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_golden_dataset"
    ADD CONSTRAINT "evaluation_golden_dataset_item_id_key" UNIQUE ("item_id");


--
-- Name: evaluation_golden_dataset evaluation_golden_dataset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_golden_dataset"
    ADD CONSTRAINT "evaluation_golden_dataset_pkey" PRIMARY KEY ("id");


--
-- Name: evaluation_results evaluation_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_results"
    ADD CONSTRAINT "evaluation_results_pkey" PRIMARY KEY ("id");


--
-- Name: evaluation_runs evaluation_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_runs"
    ADD CONSTRAINT "evaluation_runs_pkey" PRIMARY KEY ("id");


--
-- Name: evaluation_runs evaluation_runs_run_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_runs"
    ADD CONSTRAINT "evaluation_runs_run_name_key" UNIQUE ("run_name");


--
-- Name: idx_evaluation_results_evaluated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_results_evaluated_at" ON "public"."evaluation_results" USING "btree" ("evaluated_at");


--
-- Name: idx_evaluation_results_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_results_item_id" ON "public"."evaluation_results" USING "btree" ("item_id");


--
-- Name: idx_evaluation_results_overall_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_results_overall_score" ON "public"."evaluation_results" USING "btree" ("overall_score");


--
-- Name: idx_evaluation_results_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_results_run_id" ON "public"."evaluation_results" USING "btree" ("run_id");


--
-- Name: idx_evaluation_runs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_runs_created_at" ON "public"."evaluation_runs" USING "btree" ("created_at");


--
-- Name: idx_evaluation_runs_dataset; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_runs_dataset" ON "public"."evaluation_runs" USING "btree" ("dataset_name");


--
-- Name: idx_evaluation_runs_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_runs_name" ON "public"."evaluation_runs" USING "btree" ("run_name");


--
-- Name: idx_evaluation_runs_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_runs_provider" ON "public"."evaluation_runs" USING "btree" ("model_provider");


--
-- Name: idx_evaluation_runs_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_runs_started_at" ON "public"."evaluation_runs" USING "btree" ("started_at");


--
-- Name: idx_evaluation_runs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_evaluation_runs_status" ON "public"."evaluation_runs" USING "btree" ("status");


--
-- Name: idx_golden_dataset_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_golden_dataset_category" ON "public"."evaluation_golden_dataset" USING "btree" ("category");


--
-- Name: idx_golden_dataset_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_golden_dataset_created_at" ON "public"."evaluation_golden_dataset" USING "btree" ("created_at");


--
-- Name: idx_golden_dataset_difficulty; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_golden_dataset_difficulty" ON "public"."evaluation_golden_dataset" USING "btree" ("difficulty");


--
-- Name: idx_golden_dataset_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "idx_golden_dataset_name" ON "public"."evaluation_golden_dataset" USING "btree" ("dataset_name");


--
-- Name: evaluation_golden_dataset update_golden_dataset_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER "update_golden_dataset_updated_at" BEFORE UPDATE ON "public"."evaluation_golden_dataset" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();


--
-- Name: evaluation_results evaluation_results_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY "public"."evaluation_results"
    ADD CONSTRAINT "evaluation_results_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "public"."evaluation_runs"("id") ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Th7E8WFrZMZfB8H0IXUbZEm49bcGRtkauZ737knI2Qc1k8tbFvCG7P15vDeOWae

