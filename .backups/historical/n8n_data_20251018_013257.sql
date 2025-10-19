--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8
-- Dumped by pg_dump version 15.8

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auth_identity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_identity (
    "userId" uuid,
    "providerId" character varying(64) NOT NULL,
    "providerType" character varying(32) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


ALTER TABLE public.auth_identity OWNER TO postgres;

--
-- Name: auth_provider_sync_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_provider_sync_history (
    id integer NOT NULL,
    "providerType" character varying(32) NOT NULL,
    "runMode" text NOT NULL,
    status text NOT NULL,
    "startedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "endedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    scanned integer NOT NULL,
    created integer NOT NULL,
    updated integer NOT NULL,
    disabled integer NOT NULL,
    error text
);


ALTER TABLE public.auth_provider_sync_history OWNER TO postgres;

--
-- Name: auth_provider_sync_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.auth_provider_sync_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_provider_sync_history_id_seq OWNER TO postgres;

--
-- Name: auth_provider_sync_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.auth_provider_sync_history_id_seq OWNED BY public.auth_provider_sync_history.id;


--
-- Name: credentials_entity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.credentials_entity (
    name character varying(128) NOT NULL,
    data text NOT NULL,
    type character varying(128) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    id character varying(36) NOT NULL,
    "isManaged" boolean DEFAULT false NOT NULL
);


ALTER TABLE public.credentials_entity OWNER TO postgres;

--
-- Name: execution_annotation_tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.execution_annotation_tags (
    "annotationId" integer NOT NULL,
    "tagId" character varying(24) NOT NULL
);


ALTER TABLE public.execution_annotation_tags OWNER TO postgres;

--
-- Name: execution_annotations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.execution_annotations (
    id integer NOT NULL,
    "executionId" integer NOT NULL,
    vote character varying(6),
    note text,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


ALTER TABLE public.execution_annotations OWNER TO postgres;

--
-- Name: execution_annotations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.execution_annotations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.execution_annotations_id_seq OWNER TO postgres;

--
-- Name: execution_annotations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.execution_annotations_id_seq OWNED BY public.execution_annotations.id;


--
-- Name: execution_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.execution_data (
    "executionId" integer NOT NULL,
    "workflowData" json NOT NULL,
    data text NOT NULL
);


ALTER TABLE public.execution_data OWNER TO postgres;

--
-- Name: execution_entity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.execution_entity (
    id integer NOT NULL,
    finished boolean NOT NULL,
    mode character varying NOT NULL,
    "retryOf" character varying,
    "retrySuccessId" character varying,
    "startedAt" timestamp(3) with time zone,
    "stoppedAt" timestamp(3) with time zone,
    "waitTill" timestamp(3) with time zone,
    status character varying NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "deletedAt" timestamp(3) with time zone,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


ALTER TABLE public.execution_entity OWNER TO postgres;

--
-- Name: execution_entity_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.execution_entity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.execution_entity_id_seq OWNER TO postgres;

--
-- Name: execution_entity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.execution_entity_id_seq OWNED BY public.execution_entity.id;


--
-- Name: execution_metadata; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.execution_metadata (
    id integer NOT NULL,
    "executionId" integer NOT NULL,
    key character varying(255) NOT NULL,
    value text NOT NULL
);


ALTER TABLE public.execution_metadata OWNER TO postgres;

--
-- Name: execution_metadata_temp_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.execution_metadata_temp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.execution_metadata_temp_id_seq OWNER TO postgres;

--
-- Name: execution_metadata_temp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.execution_metadata_temp_id_seq OWNED BY public.execution_metadata.id;


--
-- Name: project; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project (
    id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(36) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    icon json,
    description character varying(512)
);


ALTER TABLE public.project OWNER TO postgres;

--
-- Name: project_relation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_relation (
    "projectId" character varying(36) NOT NULL,
    "userId" uuid NOT NULL,
    role character varying NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


ALTER TABLE public.project_relation OWNER TO postgres;

--
-- Name: settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.settings (
    key character varying(255) NOT NULL,
    value text NOT NULL,
    "loadOnStartup" boolean DEFAULT false NOT NULL
);


ALTER TABLE public.settings OWNER TO postgres;

--
-- Name: shared_credentials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shared_credentials (
    "credentialsId" character varying(36) NOT NULL,
    "projectId" character varying(36) NOT NULL,
    role text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


ALTER TABLE public.shared_credentials OWNER TO postgres;

--
-- Name: shared_workflow; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shared_workflow (
    "workflowId" character varying(36) NOT NULL,
    "projectId" character varying(36) NOT NULL,
    role text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


ALTER TABLE public.shared_workflow OWNER TO postgres;

--
-- Name: tag_entity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tag_entity (
    name character varying(24) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    id character varying(36) NOT NULL
);


ALTER TABLE public.tag_entity OWNER TO postgres;

--
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    id uuid DEFAULT uuid_in((OVERLAY(OVERLAY(md5((((random())::text || ':'::text) || (clock_timestamp())::text)) PLACING '4'::text FROM 13) PLACING to_hex((floor(((random() * (((11 - 8) + 1))::double precision) + (8)::double precision)))::integer) FROM 17))::cstring) NOT NULL,
    email character varying(255),
    "firstName" character varying(32),
    "lastName" character varying(32),
    password character varying(255),
    "personalizationAnswers" json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    settings json,
    disabled boolean DEFAULT false NOT NULL,
    "mfaEnabled" boolean DEFAULT false NOT NULL,
    "mfaSecret" text,
    "mfaRecoveryCodes" text,
    "lastActiveAt" date,
    "roleSlug" character varying(128) DEFAULT 'global:member'::character varying NOT NULL
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- Name: user_api_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_api_keys (
    id character varying(36) NOT NULL,
    "userId" uuid NOT NULL,
    label character varying(100) NOT NULL,
    "apiKey" character varying NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    scopes json,
    audience character varying DEFAULT 'public-api'::character varying NOT NULL
);


ALTER TABLE public.user_api_keys OWNER TO postgres;

--
-- Name: user_channel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_channel (
    user_id integer NOT NULL,
    channel_id integer NOT NULL,
    is_active boolean,
    created_at timestamp without time zone,
    last_parsed_at timestamp without time zone
);


ALTER TABLE public.user_channel OWNER TO postgres;

--
-- Name: user_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_group (
    user_id integer NOT NULL,
    group_id integer NOT NULL,
    is_active boolean DEFAULT true,
    mentions_enabled boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'UTC'::text)
);


ALTER TABLE public.user_group OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying,
    first_name character varying,
    last_name character varying,
    created_at timestamp without time zone,
    is_active boolean,
    api_id character varying,
    api_hash character varying,
    phone_number character varying,
    session_file character varying,
    is_authenticated boolean,
    last_auth_check timestamp without time zone,
    auth_error text,
    auth_session_id character varying,
    auth_session_expires timestamp without time zone,
    failed_auth_attempts integer DEFAULT 0,
    last_auth_attempt timestamp without time zone,
    is_blocked boolean DEFAULT false,
    block_expires timestamp without time zone,
    retention_days integer DEFAULT 30,
    role character varying DEFAULT 'user'::character varying,
    subscription_type character varying DEFAULT 'free'::character varying,
    subscription_expires timestamp without time zone,
    subscription_started_at timestamp without time zone,
    max_channels integer DEFAULT 3,
    invited_by integer,
    voice_queries_today integer DEFAULT 0,
    voice_queries_reset_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: variables; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.variables (
    key character varying(50) NOT NULL,
    type character varying(50) DEFAULT 'string'::character varying NOT NULL,
    value character varying(255),
    id character varying(36) NOT NULL,
    "projectId" character varying(36)
);


ALTER TABLE public.variables OWNER TO postgres;

--
-- Name: webhook_entity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.webhook_entity (
    "webhookPath" character varying NOT NULL,
    method character varying NOT NULL,
    node character varying NOT NULL,
    "webhookId" character varying,
    "pathLength" integer,
    "workflowId" character varying(36) NOT NULL
);


ALTER TABLE public.webhook_entity OWNER TO postgres;

--
-- Name: workflow_entity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflow_entity (
    name character varying(128) NOT NULL,
    active boolean NOT NULL,
    nodes json NOT NULL,
    connections json NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    settings json,
    "staticData" json,
    "pinData" json,
    "versionId" character(36),
    "triggerCount" integer DEFAULT 0 NOT NULL,
    id character varying(36) NOT NULL,
    meta json,
    "parentFolderId" character varying(36) DEFAULT NULL::character varying,
    "isArchived" boolean DEFAULT false NOT NULL
);


ALTER TABLE public.workflow_entity OWNER TO postgres;

--
-- Name: workflow_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflow_history (
    "versionId" character varying(36) NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    authors character varying(255) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    nodes json NOT NULL,
    connections json NOT NULL
);


ALTER TABLE public.workflow_history OWNER TO postgres;

--
-- Name: workflow_statistics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflow_statistics (
    count integer DEFAULT 0,
    "latestEvent" timestamp(3) with time zone,
    name character varying(128) NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "rootCount" integer DEFAULT 0
);


ALTER TABLE public.workflow_statistics OWNER TO postgres;

--
-- Name: workflows_tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflows_tags (
    "workflowId" character varying(36) NOT NULL,
    "tagId" character varying(36) NOT NULL
);


ALTER TABLE public.workflows_tags OWNER TO postgres;

--
-- Name: auth_provider_sync_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_provider_sync_history ALTER COLUMN id SET DEFAULT nextval('public.auth_provider_sync_history_id_seq'::regclass);


--
-- Name: execution_annotations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_annotations ALTER COLUMN id SET DEFAULT nextval('public.execution_annotations_id_seq'::regclass);


--
-- Name: execution_entity id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_entity ALTER COLUMN id SET DEFAULT nextval('public.execution_entity_id_seq'::regclass);


--
-- Name: execution_metadata id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_metadata ALTER COLUMN id SET DEFAULT nextval('public.execution_metadata_temp_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: auth_identity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_identity ("userId", "providerId", "providerType", "createdAt", "updatedAt") FROM stdin;
\.


--
-- Data for Name: auth_provider_sync_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_provider_sync_history (id, "providerType", "runMode", status, "startedAt", "endedAt", scanned, created, updated, disabled, error) FROM stdin;
\.


--
-- Data for Name: credentials_entity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.credentials_entity (name, data, type, "createdAt", "updatedAt", id, "isManaged") FROM stdin;
\.


--
-- Data for Name: execution_annotation_tags; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.execution_annotation_tags ("annotationId", "tagId") FROM stdin;
\.


--
-- Data for Name: execution_annotations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.execution_annotations (id, "executionId", vote, note, "createdAt", "updatedAt") FROM stdin;
\.


--
-- Data for Name: execution_data; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.execution_data ("executionId", "workflowData", data) FROM stdin;
\.


--
-- Data for Name: execution_entity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.execution_entity (id, finished, mode, "retryOf", "retrySuccessId", "startedAt", "stoppedAt", "waitTill", status, "workflowId", "deletedAt", "createdAt") FROM stdin;
\.


--
-- Data for Name: execution_metadata; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.execution_metadata (id, "executionId", key, value) FROM stdin;
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project (id, name, type, "createdAt", "updatedAt", icon, description) FROM stdin;
qMoM5hrm3iCnbqCt	Ilya Kozlov <hello@ilyasni.com>	personal	2025-10-17 22:04:40.423+00	2025-10-17 22:07:40.162+00	\N	\N
\.


--
-- Data for Name: project_relation; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.project_relation ("projectId", "userId", role, "createdAt", "updatedAt") FROM stdin;
qMoM5hrm3iCnbqCt	d6b534b2-8dec-4c39-99a0-7beaf0263716	project:personalOwner	2025-10-17 22:04:40.423+00	2025-10-17 22:04:40.423+00
\.


--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.settings (key, value, "loadOnStartup") FROM stdin;
ui.banners.dismissed	["V1"]	t
features.ldap	{"loginEnabled":false,"loginLabel":"","connectionUrl":"","allowUnauthorizedCerts":false,"connectionSecurity":"none","connectionPort":389,"baseDn":"","bindingAdminDn":"","bindingAdminPassword":"","firstNameAttribute":"","lastNameAttribute":"","emailAttribute":"","loginIdAttribute":"","ldapIdAttribute":"","userFilter":"","synchronizationEnabled":false,"synchronizationInterval":60,"searchPageSize":0,"searchTimeout":60}	t
userManagement.authenticationMethod	email	t
features.sourceControl.sshKeys	{"encryptedPrivateKey":"U2FsdGVkX1/4+WXU35RADNbA/OcSgDw6UO/pP36nNDWtm5VJmj4UUdrxZWgVeJZKQArvLeuOYvC1gyoQc/UFOaLqEvA/q64syKMY4FQUyH5O8zFw1OWId/n8PiFM0ugBtqDzSUgTEijApAySwXBBkVxlrZxfKXqeSmZhl86nKI2cLTRyyWXhbzLFXVFaSxh45fmwej8xkHxrl1BVFeiWrcNsX7Jhgrp2eXdwwUI8rS+VU4dSPfrIh7ngh2vcObvsGeZpVEhsjeLJ5Ea9GYLs5m/nv99RD3JH0dGbBkRT4lcFmb4PiHXNKSOEPLpdHzBp46Ow6ArcZYYJi1pxWkxofXSJSqtvuxhQaIYgU8v87HFcmhiESFH43ZTe+Ww2cxPCHhh6XBEzhuEALwpRPlum9u0ZDETL4DVtoKAeEyApokiSWAUa0UWXkPh4W+BrJymXpEjlxpOdC+JtwNL5g8u0uPPbC0sEcEzEMbeKeLQJn47eaEhHbHqO77nxMOWWpP8DBHrwWP5XBkbtssgMCuSHsG9ummAISJj4EKZpi5jTJzqHeFtESRNC5za0dsEy1PHM","publicKey":"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIcADpAa1dTTihJiWju20/MFnH0t5KlA5jDCTQKL8gQO n8n deploy key"}	t
features.sourceControl	{"branchName":"main","connectionType":"ssh","keyGeneratorType":"ed25519"}	t
userManagement.isInstanceOwnerSetUp	true	t
license.cert	eyJsaWNlbnNlS2V5IjoiLS0tLS1CRUdJTiBMSUNFTlNFIEtFWS0tLS0tXG5sZG56Qy91cTZwS2JlK0ZCamxtdFk4Lzd0MFUwY0lEdjVYc0VVdm5VVjN5K2RuZld0K2JtME9uMlRNcjhLNVVJXG5KRUVHZTdGdXY3V1I0TGdJaFRkcCtzVVRVbGl4RzFEM1VMVms1VFc1MndwMmpqaDg3Y0dDUDMrT3RMVEFRWnVmXG5TV3I0YTYzMllTdm5mb2NVNmNrSm9WTGk3VFgrSjlxTURITHg2MDdQangwSUp2UjI2YUpUNkJrUE1NT2FLYnhxXG5WNS9mZEE5VWFPRXFFK084NHNET0RTRHV0bytHWDdaRWJSSHNWMnZWTU94bitwKytVZU1LaG9ZRGlDSWFnUkdoXG44aU1xZXRaNmkzbE5yelhuR285eFVnYWU2a1cxVEw1em4rVHpMTHVhYitRWmZTcG0xOEVNQ2FsdHE4Q05nUC85XG5lOXRMaWZzOGljS2xBdjJTdDhHSGh3PT18fFUyRnNkR1ZrWDErR3NaYTQ0cmRjR1NIV1NTSVZoeGtXT2JGTndMXG5ZUlkrdnk3SlljbE5rS3JndXY3bnVkWno4bEZUMzB2WVhIVXl1Y0ZYNnArbjQ2U29leEwxQ1QrRTRIZkNKRGJiXG5FSkJ2OFBHZmkyOS9LVVNkWmZJSHB0REpLVXJ1b3NhS0g5T1RKemVYcGpqTkpvQ3pkNFdPMERtNkFDTEM0RnJ1XG42QUsrS2ZnTXF4REtZQnlZVEcxTGlJYXJFOWpTWVVobVZndG1sTVM1eU9ONWlqMlJRbTZvb085UjhDTzB2bmo1XG5VREplT2poNUpNMnZ2aGtrN1ZXOFR3YXdTamdmalNURmFEYlZqVzU4R0ZrRThuYnM4aXhDbTZIMlZ1N3NQZW8zXG5DSDJRYWtZQzNYNkRaZjdvSGFGRU5iZThOQUJ0WC9qSHJnQjRPRVp5UklNdkdHRS93Q0MyY3lxcGF0Z25WdVc4XG5pbDdWSTVnSkZIYWF3N2FYc2dqMUFQcVlxeW5Ya2FEZTJpTW1WSkhBYjQzR2hmLys1S3Z5SENpRjkwbkR3dFUvXG44VDVYVTRqY3BJaDgyZE9uVENRYUJzRGx4QWtoOSsyZDJVeGxneGFSU0Q0WXNQVXJWMjVNRnR4WXY4UGpqRDlSXG5HZUZoakxpbmg0MFN4dFNSelkwZW0rRkNpaU1hK0Zicnp1dFNWMTJoN3pibWw2M1RLSmpYaVNua1BxakRrMWNwXG5WczdTMFlvYVZVNTVGR2tsZnd2VEVwc0YrTkx5MDJidUIrL1FwQWh1dFpieVpYWFJ5YmxrdW9RbERVUWhwdU5BXG5aTzBTWEtYS2xKWTVCeDMxdDlXazF1bm4wSDM0QlJIVXcrclpSRUZzcWZuM1E3RTBXQWo0Mno2aXpDYytnbEVqXG5hRnBPemRRUEozNkJQQVE2ZStqcDF4aG5JZWFmYzZobnRZTXhydHMvUjBKQnpSUXNvZ25jbTEwUGZNelIyVys4XG43T2lyOFBxaDdPaXFIMVlIenJJNkJoQ05hVHNPZ3h4S0g1Qzk5QUVlcGF5Uy8rY2F1OU1Dc1BROUt0Q0NleUZjXG5pTGY4ajlkeE9rbXh1NjNWRHJxK1BtS3hJd25PK1hGdi9ndE1MbDNjMkFuZ2pTamRJSWFRVndKbmRLZlZVREhvXG41dUJjY201RUxKOUNpdU00Zm0rYVFwNlZMa2k0R3hBc1MxWTg1K0hHcnd0d1duSDNZUncyWEtGVzZ3c2QvU2h1XG55WmRIU3FreHNjWm1GN1FtTk1FSDhHZW1RWVd4NmdGYUJ6Nnd5QmY2blo3bDkzZEdhKzJlQ1RmVXA2N1k1RHpJXG5vQ2xwc3lxY3hWOGFMa2c2ZlZSdFV6MnZWT0V5aUJyL0pDLzdaSEJwWk5NdzU0aFdOWW4rdUZUK1ZWYjRYT0UxXG45eXU4RndMWDV2SVdHYURKd2cwZWMzQ1F2dWtBYzk5a01mem9oTXozNTRLTTNoZEpxUXcwT0wwV1VkWG9pOXEyXG5JeE9iSitjOVRCQWJZRFJIV21vc2xROEpEQ1ZoQWg0TzlzOE5rbVZiekhiRWJseEN6TFpRL1N6RktsRlkrN3VPXG4xODV2UU5pRHBMeWtiZXFmek90eFBtMFgweGMxNWZvaTFtaVpDdzBpaFVkUk5sZTJyM3FDclROTVlLZVpyR05JXG5CYTB2ekRSR0d3YmZHUmIzZlplSXFqK2tETWl2SHVkVVNiODFMV3A4cVI3eHIrSEkrNm5NdmFzbTRqaExobUp3XG5aMkVtRkxYaEk5ME5YbWVqbk5Hc1VPS2RWeTNRRndFQUFtYVRua1NmRFlKbTVZYVBsZ0p5RzdyWnBMU29iazh4XG4xSndidkd3aDhnNTNzL2pvKzdubWNsN3RRWlBZSExCTHRuV0owMEFVODV3WEI4UU0rU3NVcGFENlVXd05VU0Z5XG4xMmtzUkJmT012YXRPaTkvWnZ6S0lqTmJGOUprSGdyNE1PR3R6WTE2UzlQbmlnQjltbEM2cWxHTUw0TUo4VkJJXG5pV2RYayt1SVV5NjRZVm1NRVBqUzlEZjVtUzQ0d3B4eDMvcWVQbDVnMzJUT3krSzh6QWppTUEwWnZMSzY5NGcwXG56a3oyMnRmN2pwdUdXU01US1pia0NtZTV3Sy9rK2dnWFg3ejhMcXRvV0dQV2x6MHVIMnhCL05FYXllOFU4MEVMXG5ieWFLa0V5R3RqMUxvdkg0d2xnY05vckpxMW8vKzBRdDhmZTVSRlJsYVpnVjFGamVhL0xGZmsxNGFWeWxKa0JnXG5pNDZ1UlpjZ3JWS2MvR2NPOEVOVTZSSGUyZlovNzRTQkFxLzAyQXE5ZVJmZVdGQzNVVDR3ZTQ5OHRmMy9pNGdPXG5HSDhxbVVtSUlYYmQ0V3lqMjlxdFp4b0RRa0MxV0ZuSzVIYktLWm1CWGVGbVJvU20rVDFvSEdDUTZUMmt0VHdCXG5lQm9ybUV1RmNhM0lXYmRobk9hTnZaTjgzYUUzV3ZwSFpqNU1ua1g1bWRjbkFvd2tOTy9zMmJuRjZYQ2ZUOEFlXG5KZ1owaUJ3MGpmY0pCM09EdlY1UFg2V0xKZ2dqbWFRNE1QNTRMNk9HTGdWL2ZRRkVFL3lKNmRjSHhMNmFmbUFlXG41eDBWM2lkTzBqbkFjWVJCY3pJb1dzM002czB1L1JFOUtWSWl3aTJSR1NOK1ljMEFCNE8rOGc0RVF2VHp0MWF5XG5jZGdWWDVWaUV0MVhlVzRXUG5MSkM3N3k5aGl2WjZwczFyNHBjRGZmQ0g5THdqT2pnV1dBU3dFTEFqWGdiNFJuXG4zY3d5d0FkaERQeVF6TDFpbTdaMUZCNU14K2hoT1hBSUpzNzc5bmRUaTY3cndLSU50aUNyb3dpUUR1bEx6MGZzXG5rK0JZb280dnBTN1doYUZHUDljcnlLVVJLQWRIWDJMQ3B6bGJHMWRxT0dRVk0wU2xiYllWbkc3eGdyNHRtS01UXG5BM24zWGFMYnJKc1BwazNTU0RQdTA0dnA2NTlDQlpuNG8zU2Y3bEw5a0tzREhnd2p0UzZMUno5S1hvcWN3Y0NBXG5hSU56SFdhYUp2MW5jR25zT3pWUTVYZGMrditJcVZ2UnRFL1g1ajl5b25SUHJISUE9PXx8UXFqK3VaZXZ2N2FTXG5pUE9RUE1uK2c2QllPTkw5Nm5lQWRDOUVkSlMwZXlyRGpZQ29FQkJkM0JManhYUlFvMUZpelJCcWhIeXFGZ0lsXG5BR1NUUEl2ajR0Wm1QNVlZb1lRUE1qcXJiT3lsdUM3UjdFa0RLaVVjWEUvZnhMQ0QxYmxNUC9kUmVHUExjZUtpXG5nZk9EZTBPTW8yNkQ3dEFEMWNaMFlHUDQ0ZEp6WmtVRnliWFhuclI5OWtWTnEzemhtZjdRdUFHMkxhcDB5TndiXG5xcmdmcHNtNXp4aTVWaEwrNUgwelUxYkxqNzVRcm5nT0NOQ2d0NEpobU1tV3N5VjBFYTlDUnJVYTdJMFV5V1hzXG5USDFOZlNXTFViVE9PbGlSb0pjSzlMVDZ0cDJXYjNYaVMzKzRXSEl0UVdNVUVDVlo2c3BUcTBoUFB3cC9jeStkXG5ySmJlV2J4aDl3PT1cbi0tLS0tRU5EIExJQ0VOU0UgS0VZLS0tLS0iLCJ4NTA5IjoiLS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tXG5NSUlFRERDQ0FmUUNDUUNxZzJvRFQ4MHh3akFOQmdrcWhraUc5dzBCQVFVRkFEQklNUXN3Q1FZRFZRUUdFd0pFXG5SVEVQTUEwR0ExVUVDQXdHUW1WeWJHbHVNUTh3RFFZRFZRUUhEQVpDWlhKc2FXNHhGekFWQmdOVkJBTU1EbXhwXG5ZMlZ1YzJVdWJqaHVMbWx2TUI0WERUSXlNRFl5TkRBME1UQTBNRm9YRFRJek1EWXlOREEwTVRBME1Gb3dTREVMXG5NQWtHQTFVRUJoTUNSRVV4RHpBTkJnTlZCQWdNQmtKbGNteHBiakVQTUEwR0ExVUVCd3dHUW1WeWJHbHVNUmN3XG5GUVlEVlFRRERBNXNhV05sYm5ObExtNDRiaTVwYnpDQ0FTSXdEUVlKS29aSWh2Y05BUUVCQlFBRGdnRVBBRENDXG5BUW9DZ2dFQkFNQk0wNVhCNDRnNXhmbUNMd2RwVVR3QVQ4K0NCa3lMS0ZzZXprRDVLLzZXaGFYL1hyc2QvUWQwXG4yMEo3d2w1V2RIVTRjVkJtRlJqVndWemtsQ0syeVlKaThtang4c1hzR3E5UTFsYlVlTUtmVjlkc2dmdWhubEFTXG50blFaZ2x1Z09uRjJGZ1JoWGIvakswdHhUb2FvK2JORTZyNGdJRXpwa3RITEJUWXZ2aXVKbXJlZjdXYlBSdDRJXG5uZDlEN2xoeWJlYnloVjdrdXpqUUEvcFBLSFRGczhNVEhaOGhZVXhSeXJwbTMrTVl6UUQrYmpBMlUxRkljdGFVXG53UVhZV2FON3QydVR3Q3Q5ekFLc21ZL1dlT2J2bDNUWk41T05MQXp5V0dDdWxtNWN3S1IzeGJsQlp6WG5CNmdzXG5Pbk4yT0FkU3RjelRWQ3ljbThwY0ZVcnl0S1NLa0dFQ0F3RUFBVEFOQmdrcWhraUc5dzBCQVFVRkFBT0NBZ0VBXG5sSjAxd2NuMXZqWFhDSHVvaTdSMERKMWxseDErZGFmcXlFcVBBMjdKdStMWG1WVkdYUW9yUzFiOHhqVXFVa2NaXG5UQndiV0ZPNXo1ZFptTnZuYnlqYXptKzZvT2cwUE1hWXhoNlRGd3NJMlBPYmM3YkZ2MmVheXdQdC8xQ3BuYzQwXG5xVU1oZnZSeC9HQ1pQQ1d6My8yUlBKV1g5alFEU0hYQ1hxOEJXK0kvM2N1TERaeVkzZkVZQkIwcDNEdlZtYWQ2XG42V0hRYVVyaU4wL0xxeVNPcC9MWmdsbC90MDI5Z1dWdDA1WmliR29LK2NWaFpFY3NMY1VJaHJqMnVGR0ZkM0ltXG5KTGcxSktKN2pLU0JVUU9kSU1EdnNGVUY3WWRNdk11ckNZQTJzT05OOENaK0k1eFFWMUtTOWV2R0hNNWZtd2dTXG5PUEZ2UHp0RENpMC8xdVc5dE9nSHBvcnVvZGFjdCtFWk5rQVRYQ3ZaaXUydy9xdEtSSkY0VTRJVEVtNWFXMGt3XG42enVDOHh5SWt0N3ZoZHM0OFV1UlNHSDlqSnJBZW1sRWl6dEdJTGhHRHF6UUdZYmxoVVFGR01iQmI3amhlTHlDXG5MSjFXT0c2MkYxc3B4Q0tCekVXNXg2cFIxelQxbWhFZ2Q0TWtMYTZ6UFRwYWNyZDk1QWd4YUdLRUxhMVJXU0ZwXG5NdmRoR2s0TnY3aG5iOHIrQnVNUkM2aWVkUE1DelhxL001MGNOOEFnOGJ3K0oxYUZvKzBFSzJoV0phN2tpRStzXG45R3ZGalNkekNGbFVQaEtra1Vaa1NvNWFPdGNRcTdKdTZrV0JoTG9GWUtncHJscDFRVkIwc0daQTZvNkR0cWphXG5HNy9SazZ2YmFZOHdzTllLMnpCWFRUOG5laDVab1JaL1BKTFV0RUV0YzdZPVxuLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLSJ9	f
\.


--
-- Data for Name: shared_credentials; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shared_credentials ("credentialsId", "projectId", role, "createdAt", "updatedAt") FROM stdin;
\.


--
-- Data for Name: shared_workflow; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shared_workflow ("workflowId", "projectId", role, "createdAt", "updatedAt") FROM stdin;
uxeb5iQnpHfY7z79	qMoM5hrm3iCnbqCt	workflow:owner	2025-10-17 22:08:39.282+00	2025-10-17 22:08:39.282+00
7hzmwxVWHGbNfvFk	qMoM5hrm3iCnbqCt	workflow:owner	2025-10-17 22:08:53.723+00	2025-10-17 22:08:53.723+00
\.


--
-- Data for Name: tag_entity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tag_entity (name, "createdAt", "updatedAt", id) FROM stdin;
Voice AI	2025-10-17 22:08:52.371+00	2025-10-17 22:08:52.371+00	9FZMIMbEYioSlvpz
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."user" (id, email, "firstName", "lastName", password, "personalizationAnswers", "createdAt", "updatedAt", settings, disabled, "mfaEnabled", "mfaSecret", "mfaRecoveryCodes", "lastActiveAt", "roleSlug") FROM stdin;
d6b534b2-8dec-4c39-99a0-7beaf0263716	hello@ilyasni.com	Ilya	Kozlov	$2a$10$7L6dKYD6ivB4BlzwJ4wa/es26xsfWzCKslh4Ku3ZjefbQ0oBJc/Ym	\N	2025-10-17 22:04:38.317+00	2025-10-17 22:25:48.37+00	{"userActivated": false}	f	f	\N	\N	2025-10-17	global:owner
\.


--
-- Data for Name: user_api_keys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_api_keys (id, "userId", label, "apiKey", "createdAt", "updatedAt", scopes, audience) FROM stdin;
\.


--
-- Data for Name: user_channel; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_channel (user_id, channel_id, is_active, created_at, last_parsed_at) FROM stdin;
6	1	t	2025-10-06 11:25:12.696836	2025-10-17 21:51:39.459073
6	4	t	2025-10-11 12:49:36.107279	2025-10-17 21:51:39.681018
6	2	t	2025-10-11 12:48:58.957919	2025-10-17 21:51:43.278027
6	3	t	2025-10-11 12:49:19.534381	2025-10-17 21:51:45.829773
6	5	t	2025-10-11 12:49:54.632391	2025-10-17 21:51:45.970157
6	6	t	2025-10-11 12:50:16.589634	2025-10-17 21:51:46.146124
6	7	t	2025-10-11 12:50:33.787614	2025-10-17 21:51:50.087637
6	8	t	2025-10-11 12:50:49.554839	2025-10-17 21:51:50.357667
6	9	t	2025-10-11 12:51:11.87913	2025-10-17 21:51:50.796964
6	10	t	2025-10-11 12:51:38.104281	2025-10-17 21:51:50.922835
6	11	t	2025-10-11 12:51:56.267705	2025-10-17 21:51:51.04823
6	12	t	2025-10-11 12:52:15.353085	2025-10-17 21:51:51.208403
6	13	t	2025-10-11 12:52:33.675066	2025-10-17 21:51:51.361199
6	14	t	2025-10-11 12:52:51.119209	2025-10-17 21:51:51.540263
6	15	t	2025-10-11 12:53:12.203748	2025-10-17 21:51:51.67435
19	24	t	2025-10-16 21:21:35.533159	2025-10-17 21:51:51.90758
19	16	t	2025-10-12 22:13:39.80342	2025-10-17 21:51:52.105372
19	17	t	2025-10-12 22:29:06.618446	2025-10-17 21:51:52.386461
19	18	t	2025-10-12 23:03:38.482392	2025-10-17 21:51:52.650532
19	19	t	2025-10-12 23:05:46.212477	2025-10-17 21:51:52.876832
19	20	t	2025-10-12 23:07:43.292839	2025-10-17 21:51:53.14379
19	21	t	2025-10-14 17:22:38.466619	2025-10-17 21:51:53.356703
19	22	t	2025-10-14 17:27:26.451716	2025-10-17 21:51:53.542821
19	23	t	2025-10-14 17:30:00.372149	2025-10-17 21:51:53.743632
\.


--
-- Data for Name: user_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_group (user_id, group_id, is_active, mentions_enabled, created_at) FROM stdin;
19	1	t	t	2025-10-13 12:05:55.266291+00
6	2	t	t	2025-10-14 12:58:07.512724+00
19	3	t	t	2025-10-14 17:14:24.605614+00
19	4	t	t	2025-10-14 17:17:12.560192+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, telegram_id, username, first_name, last_name, created_at, is_active, api_id, api_hash, phone_number, session_file, is_authenticated, last_auth_check, auth_error, auth_session_id, auth_session_expires, failed_auth_attempts, last_auth_attempt, is_blocked, block_expires, retention_days, role, subscription_type, subscription_expires, subscription_started_at, max_channels, invited_by, voice_queries_today, voice_queries_reset_at) FROM stdin;
6	8124731874	\N	Automaniac	\N	2025-10-06 11:17:35.740589	t	182419	Z0FBQUFBQm80NlpvSm9KdzRCUWpkb3ZvNWg3NnJLWnROU3pySnRqZTN6Sms0MFZUam5teFpqQ2NiWjJqT2RodjFLUHVtejRaS2k0dk0tS0FTSlRSTHFrellHdnN5VTBZbjdHRk9OTVdxanZhV0E3SnRsV2dNSWIxS3JwMEVJQjF3WjRrd2FlTTZjNEw=	Z0FBQUFBQm80NlpvMjRyRGpMNGFDWnNuZk1tVWJ2N0d6b1Rac3JNTHlOOFhjejdTQjlUTXNvdmxKdWlsVmZvazJMNVVNQnVCVFJ3VTkzM2NYS3dWRFhxWHpkT2EzU2hqb3c9PQ==	\N	t	2025-10-12 22:49:29.352518	\N	\N	\N	0	2025-10-06 11:22:37.092364	f	\N	90	admin	premium	2025-11-11 19:34:56.775735	2025-10-12 22:49:29.353522	50	\N	2	2025-10-17 00:00:00+00
20	389326685	Ayssav	Vasilina	Radkova	2025-10-16 18:11:26.951426	t	\N	\N	\N	\N	f	\N	\N	\N	\N	0	\N	f	\N	30	user	free	\N	\N	3	\N	0	\N
18	488909738	mrf_flowers	Maria	Reunova Flowers	2025-10-12 18:09:53.366024	t	\N	\N	\N	\N	f	\N	\N	\N	\N	0	\N	f	\N	90	user	basic	\N	2025-10-12 18:31:00.071002	10	\N	0	\N
19	139883458	ilyasni	Ilya	Kozlov	2025-10-12 20:56:25.445027	t	\N	\N	\N	\N	t	2025-10-12 21:34:35.214644	\N	\N	\N	0	\N	f	\N	90	admin	premium	\N	2025-10-14 17:03:34.183012	50	\N	7	2025-10-18 00:00:00+00
\.


--
-- Data for Name: variables; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.variables (key, type, value, id, "projectId") FROM stdin;
\.


--
-- Data for Name: webhook_entity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.webhook_entity ("webhookPath", method, node, "webhookId", "pathLength", "workflowId") FROM stdin;
voice-classify	POST	Webhook	\N	\N	7hzmwxVWHGbNfvFk
mention-analyzer	POST	Webhook Trigger	\N	\N	uxeb5iQnpHfY7z79
\.


--
-- Data for Name: workflow_entity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.workflow_entity (name, active, nodes, connections, "createdAt", "updatedAt", settings, "staticData", "pinData", "versionId", "triggerCount", id, meta, "parentFolderId", "isArchived") FROM stdin;
Voice Command Classifier	t	[{"parameters":{"httpMethod":"POST","path":"voice-classify","responseMode":"lastNode","options":{"responseHeaders":{"entries":[{"name":"Content-Type","value":"application/json"}]}}},"id":"4f0704c9-8142-4b63-b017-aa83d76668fb","name":"Webhook","type":"n8n-nodes-base.webhook","typeVersion":1.1,"position":[0,0],"webhookId":"voice-classify-webhook"},{"parameters":{"assignments":{"assignments":[{"id":"transcription","name":"transcription","value":"={{ $json.body.transcription }}","type":"string"},{"id":"user_id","name":"user_id","value":"={{ $json.body.user_id }}","type":"number"}]},"options":{}},"id":"aec4f98e-210a-41de-b1a2-03db524c52a5","name":"Extract Input","type":"n8n-nodes-base.set","typeVersion":3.3,"position":[208,0]},{"parameters":{"jsCode":"const transcription = $input.first().json.transcription;\\nconst userId = $input.first().json.user_id;\\n\\nconst prompt = `Ты — классификатор голосовых команд для Telegram бота.\\n\\nДоступные команды:\\n1. /ask — поиск ответа в сохраненных постах пользователя (RAG)\\n   - Вопросы: \\"Что писали про...\\", \\"Расскажи о...\\", \\"Какие новости...\\"\\n   - Требует анализа и генерации ответа\\n\\n2. /search — гибридный поиск (посты + интернет)\\n   - Запросы: \\"Найди информацию о...\\", \\"Что такое...\\", \\"Где найти...\\"\\n   - Информационный поиск с источниками\\n\\nТранскрипция голосового сообщения:\\n\\"${transcription}\\"\\n\\nЗадача:\\nОпредели наиболее подходящую команду для этого запроса.\\n\\nВерни ТОЛЬКО JSON:\\n{\\n  \\"command\\": \\"ask\\" или \\"search\\",\\n  \\"confidence\\": 0.0-1.0,\\n  \\"reasoning\\": \\"краткое объяснение выбора\\"\\n}`;\\n\\nconst requestBody = {\\n  model: \\"GigaChat\\",\\n  messages: [\\n    {\\n      role: \\"system\\",\\n      content: \\"Ты — эксперт по классификации пользовательских запросов. Отвечай строго в формате JSON.\\"\\n    },\\n    {\\n      role: \\"user\\",\\n      content: prompt\\n    }\\n  ],\\n  temperature: 0.1,\\n  max_tokens: 150\\n};\\n\\nreturn {\\n  transcription,\\n  user_id: userId,\\n  requestBody\\n};"},"id":"ccba3b68-23f4-4287-b053-a9e4a9b1f6b8","name":"Prepare Request","type":"n8n-nodes-base.code","typeVersion":2,"position":[400,0]},{"parameters":{"method":"POST","url":"http://gpt2giga-proxy:8090/v1/chat/completions","sendBody":true,"specifyBody":"json","jsonBody":"={{ $json.requestBody }}","options":{"timeout":15000}},"id":"f9c4a8cc-59b0-4ceb-935a-c3e90f955d25","name":"GigaChat Classify","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[608,0]},{"parameters":{"jsCode":"// Парсим ответ GigaChat\\nconst item = $input.first().json;\\nconst gigachatResponse = item.choices?.[0]?.message?.content || '{}';\\n\\n// Получаем данные из Prepare Request\\nconst preparedData = $('Prepare Request').first().json;\\nconst transcription = preparedData.transcription;\\nconst userId = preparedData.user_id;\\n\\n// Очищаем от markdown backticks если есть\\nlet cleaned = gigachatResponse.trim();\\nif (cleaned.startsWith('```json')) {\\n  cleaned = cleaned.replace(/^```json\\\\s*/, '').replace(/```\\\\s*$/, '');\\n} else if (cleaned.startsWith('```')) {\\n  cleaned = cleaned.replace(/^```\\\\s*/, '').replace(/```\\\\s*$/, '');\\n}\\n\\ntry {\\n  const result = JSON.parse(cleaned);\\n  \\n  // Валидация\\n  const validCommands = ['ask', 'search'];\\n  const command = validCommands.includes(result.command) ? result.command : 'ask';\\n  const confidence = Math.min(Math.max(result.confidence || 0.5, 0), 1);\\n  \\n  return {\\n    command: command,\\n    confidence: confidence,\\n    reasoning: result.reasoning || 'No reasoning provided',\\n    original_transcription: transcription,\\n    user_id: userId\\n  };\\n} catch (e) {\\n  // Fallback: если парсинг не удался\\n  const transcriptionLower = transcription.toLowerCase();\\n  \\n  // Простая эвристика\\n  const searchKeywords = ['найди', 'найти', 'поиск', 'что такое', 'где найти', 'покажи'];\\n  const isSearch = searchKeywords.some(kw => transcriptionLower.includes(kw));\\n  \\n  return {\\n    command: isSearch ? 'search' : 'ask',\\n    confidence: 0.6,\\n    reasoning: 'Fallback: GigaChat parsing failed, used heuristics',\\n    original_transcription: transcription,\\n    user_id: userId\\n  };\\n}"},"id":"7e6098e6-eefa-4bcf-a10b-597a2c781191","name":"Parse & Validate","type":"n8n-nodes-base.code","typeVersion":2,"position":[800,0]},{"parameters":{"respondWith":"json","responseBody":"={{ $json }}","options":{}},"id":"c411a148-79c7-4f2e-a220-d5896ddc7fa5","name":"Respond to Webhook","type":"n8n-nodes-base.respondToWebhook","typeVersion":1,"position":[1008,0]}]	{"Webhook":{"main":[[{"node":"Extract Input","type":"main","index":0}]]},"Extract Input":{"main":[[{"node":"Prepare Request","type":"main","index":0}]]},"Prepare Request":{"main":[[{"node":"GigaChat Classify","type":"main","index":0}]]},"GigaChat Classify":{"main":[[{"node":"Parse & Validate","type":"main","index":0}]]},"Parse & Validate":{"main":[[{"node":"Respond to Webhook","type":"main","index":0}]]}}	2025-10-17 22:08:53.723+00	2025-10-17 22:25:54.074+00	{"executionOrder":"v1"}	\N	{}	769b6855-54ed-454f-b904-9a63e61028bf	1	7hzmwxVWHGbNfvFk	\N	\N	f
Group Mention Analyzer v2	t	[{"parameters":{"httpMethod":"POST","path":"mention-analyzer","responseMode":"lastNode","options":{}},"id":"42e7c037-552c-4c1c-a2b2-df88981993c1","name":"Webhook Trigger","type":"n8n-nodes-base.webhook","typeVersion":1,"position":[0,0],"webhookId":"mention-analyzer-webhook"},{"parameters":{"jsCode":"// Подготовка данных для анализа упоминания\\nconst items = $input.all();\\nconst data = items[0].json.body || items[0].json;\\n\\n// Извлекаем параметры\\nconst mentionContext = data.mention_context || [];\\nconst mentionedUser = data.mentioned_user;\\n\\n// Форматируем контекст\\nconst contextText = mentionContext.map((msg, idx) => {\\n  const isMention = msg.text && msg.text.includes(`@${mentionedUser}`);\\n  const prefix = isMention ? \\">>> [УПОМИНАНИЕ]\\" : \\"   \\";\\n  return `${prefix} ${msg.username}: ${msg.text}`;\\n}).join('\\\\n');\\n\\n// Создаем промпт для анализа\\nconst analysisPrompt = `Проанализируй контекст упоминания пользователя @${mentionedUser} в группе.\\\\n\\\\nКонтекст разговора:\\\\n${contextText}\\\\n\\\\nОпредели:\\\\n1. О чем разговор (контекст)\\\\n2. Почему упомянули пользователя (причина)\\\\n3. Срочность (low/medium/high)\\\\n4. Ключевые моменты\\\\n\\\\nВерни ТОЛЬКО JSON:\\\\n{\\\\n  \\"context_summary\\": \\"краткое описание контекста\\",\\\\n  \\"mention_reason\\": \\"почему упомянули\\",\\\\n  \\"urgency\\": \\"low|medium|high\\",\\\\n  \\"key_points\\": [\\"пункт1\\", \\"пункт2\\"]\\\\n}`;\\n\\nreturn [\\n  {\\n    json: {\\n      mentioned_user: mentionedUser,\\n      context_text: contextText,\\n      message_count: mentionContext.length,\\n      analysis_prompt: analysisPrompt\\n    }\\n  }\\n];"},"id":"ebb3ee72-5c80-42c0-b566-0b90477d2f18","name":"Prepare Mention Prompt","type":"n8n-nodes-base.code","typeVersion":2,"position":[208,0]},{"parameters":{"method":"POST","url":"http://gpt2giga-proxy:8090/v1/chat/completions","sendHeaders":true,"headerParameters":{"parameters":[{"name":"Content-Type","value":"application/json"}]},"sendBody":true,"specifyBody":"json","jsonBody":"={{ {\\"model\\": \\"GigaChat\\", \\"messages\\": [{\\"role\\": \\"system\\", \\"content\\": \\"Ты - аналитик контекста. Анализируй причины упоминаний пользователей в диалогах.\\"}, {\\"role\\": \\"user\\", \\"content\\": $json.analysis_prompt}], \\"temperature\\": 0.3, \\"max_tokens\\": 400} }}","options":{"timeout":60000}},"id":"786c80a9-80f7-47e7-958b-c7a7796a0a02","name":"Analyze Mention Context","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[400,0]},{"parameters":{"jsCode":"// Форматирование результата анализа упоминания\\nconst items = $input.all();\\nconst analysisResponse = items[0].json.choices?.[0]?.message?.content || '{}';\\n\\nlet result = {\\n  context_summary: \\"\\",\\n  mention_reason: \\"\\",\\n  urgency: \\"medium\\",\\n  key_points: []\\n};\\n\\ntry {\\n  // Парсим JSON ответ\\n  const parsed = JSON.parse(analysisResponse);\\n  result = {\\n    context_summary: parsed.context_summary || \\"\\",\\n    mention_reason: parsed.mention_reason || \\"\\",\\n    urgency: parsed.urgency || \\"medium\\",\\n    key_points: parsed.key_points || []\\n  };\\n} catch (e) {\\n  // Fallback: извлекаем JSON из текста\\n  const jsonMatch = analysisResponse.match(/\\\\{[\\\\s\\\\S]*\\\\}/);\\n  if (jsonMatch) {\\n    try {\\n      const parsed = JSON.parse(jsonMatch[0]);\\n      result = {\\n        context_summary: parsed.context_summary || \\"\\",\\n        mention_reason: parsed.mention_reason || \\"\\",\\n        urgency: parsed.urgency || \\"medium\\",\\n        key_points: parsed.key_points || []\\n      };\\n    } catch (e2) {\\n      // Используем fallback значения\\n      result = {\\n        context_summary: \\"Не удалось проанализировать контекст\\",\\n        mention_reason: \\"Требуется внимание\\",\\n        urgency: \\"medium\\",\\n        key_points: [\\"Проверьте сообщение вручную\\"]\\n      };\\n    }\\n  }\\n}\\n\\nreturn [\\n  {\\n    json: result\\n  }\\n];"},"id":"cb2ae5a0-3e9c-4552-8181-09a931a522cd","name":"Format Mention Response","type":"n8n-nodes-base.code","typeVersion":2,"position":[608,0]},{"parameters":{"respondWith":"json","responseBody":"={{ $json }}","options":{}},"id":"5f22a1eb-9244-47b5-8fe8-86279401d222","name":"Respond to Webhook","type":"n8n-nodes-base.respondToWebhook","typeVersion":1,"position":[800,0]}]	{"Webhook Trigger":{"main":[[{"node":"Prepare Mention Prompt","type":"main","index":0}]]},"Prepare Mention Prompt":{"main":[[{"node":"Analyze Mention Context","type":"main","index":0}]]},"Analyze Mention Context":{"main":[[{"node":"Format Mention Response","type":"main","index":0}]]},"Format Mention Response":{"main":[[{"node":"Respond to Webhook","type":"main","index":0}]]}}	2025-10-17 22:08:39.282+00	2025-10-17 22:25:55.726+00	{"executionOrder":"v1"}	\N	{}	bd70ef0d-4699-48fe-93d4-b9e0cb41b915	1	uxeb5iQnpHfY7z79	\N	\N	f
\.


--
-- Data for Name: workflow_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.workflow_history ("versionId", "workflowId", authors, "createdAt", "updatedAt", nodes, connections) FROM stdin;
bd70ef0d-4699-48fe-93d4-b9e0cb41b915	uxeb5iQnpHfY7z79	Ilya Kozlov	2025-10-17 22:08:39.307+00	2025-10-17 22:08:39.307+00	[{"parameters":{"httpMethod":"POST","path":"mention-analyzer","responseMode":"lastNode","options":{}},"id":"42e7c037-552c-4c1c-a2b2-df88981993c1","name":"Webhook Trigger","type":"n8n-nodes-base.webhook","typeVersion":1,"position":[0,0],"webhookId":"mention-analyzer-webhook"},{"parameters":{"jsCode":"// Подготовка данных для анализа упоминания\\nconst items = $input.all();\\nconst data = items[0].json.body || items[0].json;\\n\\n// Извлекаем параметры\\nconst mentionContext = data.mention_context || [];\\nconst mentionedUser = data.mentioned_user;\\n\\n// Форматируем контекст\\nconst contextText = mentionContext.map((msg, idx) => {\\n  const isMention = msg.text && msg.text.includes(`@${mentionedUser}`);\\n  const prefix = isMention ? \\">>> [УПОМИНАНИЕ]\\" : \\"   \\";\\n  return `${prefix} ${msg.username}: ${msg.text}`;\\n}).join('\\\\n');\\n\\n// Создаем промпт для анализа\\nconst analysisPrompt = `Проанализируй контекст упоминания пользователя @${mentionedUser} в группе.\\\\n\\\\nКонтекст разговора:\\\\n${contextText}\\\\n\\\\nОпредели:\\\\n1. О чем разговор (контекст)\\\\n2. Почему упомянули пользователя (причина)\\\\n3. Срочность (low/medium/high)\\\\n4. Ключевые моменты\\\\n\\\\nВерни ТОЛЬКО JSON:\\\\n{\\\\n  \\"context_summary\\": \\"краткое описание контекста\\",\\\\n  \\"mention_reason\\": \\"почему упомянули\\",\\\\n  \\"urgency\\": \\"low|medium|high\\",\\\\n  \\"key_points\\": [\\"пункт1\\", \\"пункт2\\"]\\\\n}`;\\n\\nreturn [\\n  {\\n    json: {\\n      mentioned_user: mentionedUser,\\n      context_text: contextText,\\n      message_count: mentionContext.length,\\n      analysis_prompt: analysisPrompt\\n    }\\n  }\\n];"},"id":"ebb3ee72-5c80-42c0-b566-0b90477d2f18","name":"Prepare Mention Prompt","type":"n8n-nodes-base.code","typeVersion":2,"position":[208,0]},{"parameters":{"method":"POST","url":"http://gpt2giga-proxy:8090/v1/chat/completions","sendHeaders":true,"headerParameters":{"parameters":[{"name":"Content-Type","value":"application/json"}]},"sendBody":true,"specifyBody":"json","jsonBody":"={{ {\\"model\\": \\"GigaChat\\", \\"messages\\": [{\\"role\\": \\"system\\", \\"content\\": \\"Ты - аналитик контекста. Анализируй причины упоминаний пользователей в диалогах.\\"}, {\\"role\\": \\"user\\", \\"content\\": $json.analysis_prompt}], \\"temperature\\": 0.3, \\"max_tokens\\": 400} }}","options":{"timeout":60000}},"id":"786c80a9-80f7-47e7-958b-c7a7796a0a02","name":"Analyze Mention Context","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[400,0]},{"parameters":{"jsCode":"// Форматирование результата анализа упоминания\\nconst items = $input.all();\\nconst analysisResponse = items[0].json.choices?.[0]?.message?.content || '{}';\\n\\nlet result = {\\n  context_summary: \\"\\",\\n  mention_reason: \\"\\",\\n  urgency: \\"medium\\",\\n  key_points: []\\n};\\n\\ntry {\\n  // Парсим JSON ответ\\n  const parsed = JSON.parse(analysisResponse);\\n  result = {\\n    context_summary: parsed.context_summary || \\"\\",\\n    mention_reason: parsed.mention_reason || \\"\\",\\n    urgency: parsed.urgency || \\"medium\\",\\n    key_points: parsed.key_points || []\\n  };\\n} catch (e) {\\n  // Fallback: извлекаем JSON из текста\\n  const jsonMatch = analysisResponse.match(/\\\\{[\\\\s\\\\S]*\\\\}/);\\n  if (jsonMatch) {\\n    try {\\n      const parsed = JSON.parse(jsonMatch[0]);\\n      result = {\\n        context_summary: parsed.context_summary || \\"\\",\\n        mention_reason: parsed.mention_reason || \\"\\",\\n        urgency: parsed.urgency || \\"medium\\",\\n        key_points: parsed.key_points || []\\n      };\\n    } catch (e2) {\\n      // Используем fallback значения\\n      result = {\\n        context_summary: \\"Не удалось проанализировать контекст\\",\\n        mention_reason: \\"Требуется внимание\\",\\n        urgency: \\"medium\\",\\n        key_points: [\\"Проверьте сообщение вручную\\"]\\n      };\\n    }\\n  }\\n}\\n\\nreturn [\\n  {\\n    json: result\\n  }\\n];"},"id":"cb2ae5a0-3e9c-4552-8181-09a931a522cd","name":"Format Mention Response","type":"n8n-nodes-base.code","typeVersion":2,"position":[608,0]},{"parameters":{"respondWith":"json","responseBody":"={{ $json }}","options":{}},"id":"5f22a1eb-9244-47b5-8fe8-86279401d222","name":"Respond to Webhook","type":"n8n-nodes-base.respondToWebhook","typeVersion":1,"position":[800,0]}]	{"Webhook Trigger":{"main":[[{"node":"Prepare Mention Prompt","type":"main","index":0}]]},"Prepare Mention Prompt":{"main":[[{"node":"Analyze Mention Context","type":"main","index":0}]]},"Analyze Mention Context":{"main":[[{"node":"Format Mention Response","type":"main","index":0}]]},"Format Mention Response":{"main":[[{"node":"Respond to Webhook","type":"main","index":0}]]}}
769b6855-54ed-454f-b904-9a63e61028bf	7hzmwxVWHGbNfvFk	Ilya Kozlov	2025-10-17 22:08:53.748+00	2025-10-17 22:08:53.748+00	[{"parameters":{"httpMethod":"POST","path":"voice-classify","responseMode":"lastNode","options":{"responseHeaders":{"entries":[{"name":"Content-Type","value":"application/json"}]}}},"id":"4f0704c9-8142-4b63-b017-aa83d76668fb","name":"Webhook","type":"n8n-nodes-base.webhook","typeVersion":1.1,"position":[0,0],"webhookId":"voice-classify-webhook"},{"parameters":{"assignments":{"assignments":[{"id":"transcription","name":"transcription","value":"={{ $json.body.transcription }}","type":"string"},{"id":"user_id","name":"user_id","value":"={{ $json.body.user_id }}","type":"number"}]},"options":{}},"id":"aec4f98e-210a-41de-b1a2-03db524c52a5","name":"Extract Input","type":"n8n-nodes-base.set","typeVersion":3.3,"position":[208,0]},{"parameters":{"jsCode":"const transcription = $input.first().json.transcription;\\nconst userId = $input.first().json.user_id;\\n\\nconst prompt = `Ты — классификатор голосовых команд для Telegram бота.\\n\\nДоступные команды:\\n1. /ask — поиск ответа в сохраненных постах пользователя (RAG)\\n   - Вопросы: \\"Что писали про...\\", \\"Расскажи о...\\", \\"Какие новости...\\"\\n   - Требует анализа и генерации ответа\\n\\n2. /search — гибридный поиск (посты + интернет)\\n   - Запросы: \\"Найди информацию о...\\", \\"Что такое...\\", \\"Где найти...\\"\\n   - Информационный поиск с источниками\\n\\nТранскрипция голосового сообщения:\\n\\"${transcription}\\"\\n\\nЗадача:\\nОпредели наиболее подходящую команду для этого запроса.\\n\\nВерни ТОЛЬКО JSON:\\n{\\n  \\"command\\": \\"ask\\" или \\"search\\",\\n  \\"confidence\\": 0.0-1.0,\\n  \\"reasoning\\": \\"краткое объяснение выбора\\"\\n}`;\\n\\nconst requestBody = {\\n  model: \\"GigaChat\\",\\n  messages: [\\n    {\\n      role: \\"system\\",\\n      content: \\"Ты — эксперт по классификации пользовательских запросов. Отвечай строго в формате JSON.\\"\\n    },\\n    {\\n      role: \\"user\\",\\n      content: prompt\\n    }\\n  ],\\n  temperature: 0.1,\\n  max_tokens: 150\\n};\\n\\nreturn {\\n  transcription,\\n  user_id: userId,\\n  requestBody\\n};"},"id":"ccba3b68-23f4-4287-b053-a9e4a9b1f6b8","name":"Prepare Request","type":"n8n-nodes-base.code","typeVersion":2,"position":[400,0]},{"parameters":{"method":"POST","url":"http://gpt2giga-proxy:8090/v1/chat/completions","sendBody":true,"specifyBody":"json","jsonBody":"={{ $json.requestBody }}","options":{"timeout":15000}},"id":"f9c4a8cc-59b0-4ceb-935a-c3e90f955d25","name":"GigaChat Classify","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[608,0]},{"parameters":{"jsCode":"// Парсим ответ GigaChat\\nconst item = $input.first().json;\\nconst gigachatResponse = item.choices?.[0]?.message?.content || '{}';\\n\\n// Получаем данные из Prepare Request\\nconst preparedData = $('Prepare Request').first().json;\\nconst transcription = preparedData.transcription;\\nconst userId = preparedData.user_id;\\n\\n// Очищаем от markdown backticks если есть\\nlet cleaned = gigachatResponse.trim();\\nif (cleaned.startsWith('```json')) {\\n  cleaned = cleaned.replace(/^```json\\\\s*/, '').replace(/```\\\\s*$/, '');\\n} else if (cleaned.startsWith('```')) {\\n  cleaned = cleaned.replace(/^```\\\\s*/, '').replace(/```\\\\s*$/, '');\\n}\\n\\ntry {\\n  const result = JSON.parse(cleaned);\\n  \\n  // Валидация\\n  const validCommands = ['ask', 'search'];\\n  const command = validCommands.includes(result.command) ? result.command : 'ask';\\n  const confidence = Math.min(Math.max(result.confidence || 0.5, 0), 1);\\n  \\n  return {\\n    command: command,\\n    confidence: confidence,\\n    reasoning: result.reasoning || 'No reasoning provided',\\n    original_transcription: transcription,\\n    user_id: userId\\n  };\\n} catch (e) {\\n  // Fallback: если парсинг не удался\\n  const transcriptionLower = transcription.toLowerCase();\\n  \\n  // Простая эвристика\\n  const searchKeywords = ['найди', 'найти', 'поиск', 'что такое', 'где найти', 'покажи'];\\n  const isSearch = searchKeywords.some(kw => transcriptionLower.includes(kw));\\n  \\n  return {\\n    command: isSearch ? 'search' : 'ask',\\n    confidence: 0.6,\\n    reasoning: 'Fallback: GigaChat parsing failed, used heuristics',\\n    original_transcription: transcription,\\n    user_id: userId\\n  };\\n}"},"id":"7e6098e6-eefa-4bcf-a10b-597a2c781191","name":"Parse & Validate","type":"n8n-nodes-base.code","typeVersion":2,"position":[800,0]},{"parameters":{"respondWith":"json","responseBody":"={{ $json }}","options":{}},"id":"c411a148-79c7-4f2e-a220-d5896ddc7fa5","name":"Respond to Webhook","type":"n8n-nodes-base.respondToWebhook","typeVersion":1,"position":[1008,0]}]	{"Webhook":{"main":[[{"node":"Extract Input","type":"main","index":0}]]},"Extract Input":{"main":[[{"node":"Prepare Request","type":"main","index":0}]]},"Prepare Request":{"main":[[{"node":"GigaChat Classify","type":"main","index":0}]]},"GigaChat Classify":{"main":[[{"node":"Parse & Validate","type":"main","index":0}]]},"Parse & Validate":{"main":[[{"node":"Respond to Webhook","type":"main","index":0}]]}}
\.


--
-- Data for Name: workflow_statistics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.workflow_statistics (count, "latestEvent", name, "workflowId", "rootCount") FROM stdin;
\.


--
-- Data for Name: workflows_tags; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.workflows_tags ("workflowId", "tagId") FROM stdin;
7hzmwxVWHGbNfvFk	9FZMIMbEYioSlvpz
\.


--
-- Name: auth_provider_sync_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_provider_sync_history_id_seq', 1, false);


--
-- Name: execution_annotations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.execution_annotations_id_seq', 1, false);


--
-- Name: execution_entity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.execution_entity_id_seq', 1, false);


--
-- Name: execution_metadata_temp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.execution_metadata_temp_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 20, true);


--
-- Name: execution_metadata PK_17a0b6284f8d626aae88e1c16e4; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_metadata
    ADD CONSTRAINT "PK_17a0b6284f8d626aae88e1c16e4" PRIMARY KEY (id);


--
-- Name: project_relation PK_1caaa312a5d7184a003be0f0cb6; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "PK_1caaa312a5d7184a003be0f0cb6" PRIMARY KEY ("projectId", "userId");


--
-- Name: project PK_4d68b1358bb5b766d3e78f32f57; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT "PK_4d68b1358bb5b766d3e78f32f57" PRIMARY KEY (id);


--
-- Name: shared_workflow PK_5ba87620386b847201c9531c58f; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_workflow
    ADD CONSTRAINT "PK_5ba87620386b847201c9531c58f" PRIMARY KEY ("workflowId", "projectId");


--
-- Name: execution_annotations PK_7afcf93ffa20c4252869a7c6a23; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_annotations
    ADD CONSTRAINT "PK_7afcf93ffa20c4252869a7c6a23" PRIMARY KEY (id);


--
-- Name: shared_credentials PK_8ef3a59796a228913f251779cff; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_credentials
    ADD CONSTRAINT "PK_8ef3a59796a228913f251779cff" PRIMARY KEY ("credentialsId", "projectId");


--
-- Name: user_api_keys PK_978fa5caa3468f463dac9d92e69; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_api_keys
    ADD CONSTRAINT "PK_978fa5caa3468f463dac9d92e69" PRIMARY KEY (id);


--
-- Name: execution_annotation_tags PK_979ec03d31294cca484be65d11f; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_annotation_tags
    ADD CONSTRAINT "PK_979ec03d31294cca484be65d11f" PRIMARY KEY ("annotationId", "tagId");


--
-- Name: webhook_entity PK_b21ace2e13596ccd87dc9bf4ea6; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.webhook_entity
    ADD CONSTRAINT "PK_b21ace2e13596ccd87dc9bf4ea6" PRIMARY KEY ("webhookPath", method);


--
-- Name: workflow_history PK_b6572dd6173e4cd06fe79937b58; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_history
    ADD CONSTRAINT "PK_b6572dd6173e4cd06fe79937b58" PRIMARY KEY ("versionId");


--
-- Name: settings PK_dc0fe14e6d9943f268e7b119f69ab8bd; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT "PK_dc0fe14e6d9943f268e7b119f69ab8bd" PRIMARY KEY (key);


--
-- Name: user PK_ea8f538c94b6e352418254ed6474a81f; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT "PK_ea8f538c94b6e352418254ed6474a81f" PRIMARY KEY (id);


--
-- Name: user UQ_e12875dfb3b1d92d7d7c5377e2; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT "UQ_e12875dfb3b1d92d7d7c5377e2" UNIQUE (email);


--
-- Name: auth_identity auth_identity_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_identity
    ADD CONSTRAINT auth_identity_pkey PRIMARY KEY ("providerId", "providerType");


--
-- Name: auth_provider_sync_history auth_provider_sync_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_provider_sync_history
    ADD CONSTRAINT auth_provider_sync_history_pkey PRIMARY KEY (id);


--
-- Name: credentials_entity credentials_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credentials_entity
    ADD CONSTRAINT credentials_entity_pkey PRIMARY KEY (id);


--
-- Name: execution_data execution_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_data
    ADD CONSTRAINT execution_data_pkey PRIMARY KEY ("executionId");


--
-- Name: execution_entity pk_e3e63bbf986767844bbe1166d4e; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_entity
    ADD CONSTRAINT pk_e3e63bbf986767844bbe1166d4e PRIMARY KEY (id);


--
-- Name: workflow_statistics pk_workflow_statistics; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_statistics
    ADD CONSTRAINT pk_workflow_statistics PRIMARY KEY ("workflowId", name);


--
-- Name: workflows_tags pk_workflows_tags; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflows_tags
    ADD CONSTRAINT pk_workflows_tags PRIMARY KEY ("workflowId", "tagId");


--
-- Name: tag_entity tag_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tag_entity
    ADD CONSTRAINT tag_entity_pkey PRIMARY KEY (id);


--
-- Name: user_channel user_channel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_channel
    ADD CONSTRAINT user_channel_pkey PRIMARY KEY (user_id, channel_id);


--
-- Name: user_group user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group
    ADD CONSTRAINT user_group_pkey PRIMARY KEY (user_id, group_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: variables variables_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.variables
    ADD CONSTRAINT variables_pkey PRIMARY KEY (id);


--
-- Name: workflow_entity workflow_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_entity
    ADD CONSTRAINT workflow_entity_pkey PRIMARY KEY (id);


--
-- Name: IDX_1e31657f5fe46816c34be7c1b4; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IDX_1e31657f5fe46816c34be7c1b4" ON public.workflow_history USING btree ("workflowId");


--
-- Name: IDX_1ef35bac35d20bdae979d917a3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "IDX_1ef35bac35d20bdae979d917a3" ON public.user_api_keys USING btree ("apiKey");


--
-- Name: IDX_5f0643f6717905a05164090dde; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IDX_5f0643f6717905a05164090dde" ON public.project_relation USING btree ("userId");


--
-- Name: IDX_61448d56d61802b5dfde5cdb00; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IDX_61448d56d61802b5dfde5cdb00" ON public.project_relation USING btree ("projectId");


--
-- Name: IDX_63d7bbae72c767cf162d459fcc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "IDX_63d7bbae72c767cf162d459fcc" ON public.user_api_keys USING btree ("userId", label);


--
-- Name: IDX_97f863fa83c4786f1956508496; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "IDX_97f863fa83c4786f1956508496" ON public.execution_annotations USING btree ("executionId");


--
-- Name: IDX_a3697779b366e131b2bbdae297; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IDX_a3697779b366e131b2bbdae297" ON public.execution_annotation_tags USING btree ("tagId");


--
-- Name: IDX_c1519757391996eb06064f0e7c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IDX_c1519757391996eb06064f0e7c" ON public.execution_annotation_tags USING btree ("annotationId");


--
-- Name: IDX_cec8eea3bf49551482ccb4933e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "IDX_cec8eea3bf49551482ccb4933e" ON public.execution_metadata USING btree ("executionId", key);


--
-- Name: IDX_execution_entity_deletedAt; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IDX_execution_entity_deletedAt" ON public.execution_entity USING btree ("deletedAt");


--
-- Name: IDX_workflow_entity_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "IDX_workflow_entity_name" ON public.workflow_entity USING btree (name);


--
-- Name: idx_07fde106c0b471d8cc80a64fc8; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_07fde106c0b471d8cc80a64fc8 ON public.credentials_entity USING btree (type);


--
-- Name: idx_16f4436789e804e3e1c9eeb240; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_16f4436789e804e3e1c9eeb240 ON public.webhook_entity USING btree ("webhookId", method, "pathLength");


--
-- Name: idx_812eb05f7451ca757fb98444ce; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_812eb05f7451ca757fb98444ce ON public.tag_entity USING btree (name);


--
-- Name: idx_execution_entity_stopped_at_status_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_entity_stopped_at_status_deleted_at ON public.execution_entity USING btree ("stoppedAt", status, "deletedAt") WHERE (("stoppedAt" IS NOT NULL) AND ("deletedAt" IS NULL));


--
-- Name: idx_execution_entity_wait_till_status_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_entity_wait_till_status_deleted_at ON public.execution_entity USING btree ("waitTill", status, "deletedAt") WHERE (("waitTill" IS NOT NULL) AND ("deletedAt" IS NULL));


--
-- Name: idx_execution_entity_workflow_id_started_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_entity_workflow_id_started_at ON public.execution_entity USING btree ("workflowId", "startedAt") WHERE (("startedAt" IS NOT NULL) AND ("deletedAt" IS NULL));


--
-- Name: idx_user_group_group_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_group_group_id ON public.user_group USING btree (group_id);


--
-- Name: idx_user_group_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_group_user_id ON public.user_group USING btree (user_id);


--
-- Name: idx_workflows_tags_workflow_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_workflows_tags_workflow_id ON public.workflows_tags USING btree ("workflowId");


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: pk_credentials_entity_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX pk_credentials_entity_id ON public.credentials_entity USING btree (id);


--
-- Name: pk_tag_entity_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX pk_tag_entity_id ON public.tag_entity USING btree (id);


--
-- Name: pk_workflow_entity_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX pk_workflow_entity_id ON public.workflow_entity USING btree (id);


--
-- Name: project_relation_role_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX project_relation_role_idx ON public.project_relation USING btree (role);


--
-- Name: project_relation_role_project_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX project_relation_role_project_idx ON public.project_relation USING btree ("projectId", role);


--
-- Name: user_role_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_role_idx ON public."user" USING btree ("roleSlug");


--
-- Name: variables_global_key_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX variables_global_key_unique ON public.variables USING btree (key) WHERE ("projectId" IS NULL);


--
-- Name: variables_project_key_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX variables_project_key_unique ON public.variables USING btree ("projectId", key) WHERE ("projectId" IS NOT NULL);


--
-- Name: workflow_history FK_1e31657f5fe46816c34be7c1b4b; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_history
    ADD CONSTRAINT "FK_1e31657f5fe46816c34be7c1b4b" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: execution_metadata FK_31d0b4c93fb85ced26f6005cda3; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_metadata
    ADD CONSTRAINT "FK_31d0b4c93fb85ced26f6005cda3" FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE CASCADE;


--
-- Name: shared_credentials FK_416f66fc846c7c442970c094ccf; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_credentials
    ADD CONSTRAINT "FK_416f66fc846c7c442970c094ccf" FOREIGN KEY ("credentialsId") REFERENCES public.credentials_entity(id) ON DELETE CASCADE;


--
-- Name: variables FK_42f6c766f9f9d2edcc15bdd6e9b; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.variables
    ADD CONSTRAINT "FK_42f6c766f9f9d2edcc15bdd6e9b" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: project_relation FK_5f0643f6717905a05164090dde7; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "FK_5f0643f6717905a05164090dde7" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: project_relation FK_61448d56d61802b5dfde5cdb002; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "FK_61448d56d61802b5dfde5cdb002" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: shared_credentials FK_812c2852270da1247756e77f5a4; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_credentials
    ADD CONSTRAINT "FK_812c2852270da1247756e77f5a4" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: execution_annotations FK_97f863fa83c4786f19565084960; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_annotations
    ADD CONSTRAINT "FK_97f863fa83c4786f19565084960" FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE CASCADE;


--
-- Name: execution_annotation_tags FK_a3697779b366e131b2bbdae2976; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_annotation_tags
    ADD CONSTRAINT "FK_a3697779b366e131b2bbdae2976" FOREIGN KEY ("tagId") REFERENCES public.annotation_tag_entity(id) ON DELETE CASCADE;


--
-- Name: shared_workflow FK_a45ea5f27bcfdc21af9b4188560; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_workflow
    ADD CONSTRAINT "FK_a45ea5f27bcfdc21af9b4188560" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: execution_annotation_tags FK_c1519757391996eb06064f0e7c8; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_annotation_tags
    ADD CONSTRAINT "FK_c1519757391996eb06064f0e7c8" FOREIGN KEY ("annotationId") REFERENCES public.execution_annotations(id) ON DELETE CASCADE;


--
-- Name: project_relation FK_c6b99592dc96b0d836d7a21db91; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "FK_c6b99592dc96b0d836d7a21db91" FOREIGN KEY (role) REFERENCES public.role(slug);


--
-- Name: shared_workflow FK_daa206a04983d47d0a9c34649ce; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_workflow
    ADD CONSTRAINT "FK_daa206a04983d47d0a9c34649ce" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: user_api_keys FK_e131705cbbc8fb589889b02d457; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_api_keys
    ADD CONSTRAINT "FK_e131705cbbc8fb589889b02d457" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: user FK_eaea92ee7bfb9c1b6cd01505d56; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT "FK_eaea92ee7bfb9c1b6cd01505d56" FOREIGN KEY ("roleSlug") REFERENCES public.role(slug);


--
-- Name: auth_identity auth_identity_userId_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_identity
    ADD CONSTRAINT "auth_identity_userId_fkey" FOREIGN KEY ("userId") REFERENCES public."user"(id);


--
-- Name: execution_data execution_data_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_data
    ADD CONSTRAINT execution_data_fk FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE CASCADE;


--
-- Name: execution_entity fk_execution_entity_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_entity
    ADD CONSTRAINT fk_execution_entity_workflow_id FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: webhook_entity fk_webhook_entity_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.webhook_entity
    ADD CONSTRAINT fk_webhook_entity_workflow_id FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: workflow_entity fk_workflow_parent_folder; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_entity
    ADD CONSTRAINT fk_workflow_parent_folder FOREIGN KEY ("parentFolderId") REFERENCES public.folder(id) ON DELETE CASCADE;


--
-- Name: workflow_statistics fk_workflow_statistics_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_statistics
    ADD CONSTRAINT fk_workflow_statistics_workflow_id FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: workflows_tags fk_workflows_tags_tag_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflows_tags
    ADD CONSTRAINT fk_workflows_tags_tag_id FOREIGN KEY ("tagId") REFERENCES public.tag_entity(id) ON DELETE CASCADE;


--
-- Name: workflows_tags fk_workflows_tags_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflows_tags
    ADD CONSTRAINT fk_workflows_tags_workflow_id FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: user_channel user_channel_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_channel
    ADD CONSTRAINT user_channel_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE CASCADE;


--
-- Name: user_channel user_channel_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_channel
    ADD CONSTRAINT user_channel_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_group user_group_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group
    ADD CONSTRAINT user_group_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;


--
-- Name: user_group user_group_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_group
    ADD CONSTRAINT user_group_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: TABLE auth_identity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.auth_identity TO anon;
GRANT ALL ON TABLE public.auth_identity TO authenticated;
GRANT ALL ON TABLE public.auth_identity TO service_role;


--
-- Name: TABLE auth_provider_sync_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.auth_provider_sync_history TO anon;
GRANT ALL ON TABLE public.auth_provider_sync_history TO authenticated;
GRANT ALL ON TABLE public.auth_provider_sync_history TO service_role;


--
-- Name: SEQUENCE auth_provider_sync_history_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.auth_provider_sync_history_id_seq TO anon;
GRANT ALL ON SEQUENCE public.auth_provider_sync_history_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.auth_provider_sync_history_id_seq TO service_role;


--
-- Name: TABLE credentials_entity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.credentials_entity TO anon;
GRANT ALL ON TABLE public.credentials_entity TO authenticated;
GRANT ALL ON TABLE public.credentials_entity TO service_role;


--
-- Name: TABLE execution_annotation_tags; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.execution_annotation_tags TO anon;
GRANT ALL ON TABLE public.execution_annotation_tags TO authenticated;
GRANT ALL ON TABLE public.execution_annotation_tags TO service_role;


--
-- Name: TABLE execution_annotations; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.execution_annotations TO anon;
GRANT ALL ON TABLE public.execution_annotations TO authenticated;
GRANT ALL ON TABLE public.execution_annotations TO service_role;


--
-- Name: SEQUENCE execution_annotations_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.execution_annotations_id_seq TO anon;
GRANT ALL ON SEQUENCE public.execution_annotations_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.execution_annotations_id_seq TO service_role;


--
-- Name: TABLE execution_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.execution_data TO anon;
GRANT ALL ON TABLE public.execution_data TO authenticated;
GRANT ALL ON TABLE public.execution_data TO service_role;


--
-- Name: TABLE execution_entity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.execution_entity TO anon;
GRANT ALL ON TABLE public.execution_entity TO authenticated;
GRANT ALL ON TABLE public.execution_entity TO service_role;


--
-- Name: SEQUENCE execution_entity_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.execution_entity_id_seq TO anon;
GRANT ALL ON SEQUENCE public.execution_entity_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.execution_entity_id_seq TO service_role;


--
-- Name: TABLE execution_metadata; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.execution_metadata TO anon;
GRANT ALL ON TABLE public.execution_metadata TO authenticated;
GRANT ALL ON TABLE public.execution_metadata TO service_role;


--
-- Name: SEQUENCE execution_metadata_temp_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.execution_metadata_temp_id_seq TO anon;
GRANT ALL ON SEQUENCE public.execution_metadata_temp_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.execution_metadata_temp_id_seq TO service_role;


--
-- Name: TABLE project; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.project TO anon;
GRANT ALL ON TABLE public.project TO authenticated;
GRANT ALL ON TABLE public.project TO service_role;


--
-- Name: TABLE project_relation; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.project_relation TO anon;
GRANT ALL ON TABLE public.project_relation TO authenticated;
GRANT ALL ON TABLE public.project_relation TO service_role;


--
-- Name: TABLE settings; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.settings TO anon;
GRANT ALL ON TABLE public.settings TO authenticated;
GRANT ALL ON TABLE public.settings TO service_role;


--
-- Name: TABLE shared_credentials; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.shared_credentials TO anon;
GRANT ALL ON TABLE public.shared_credentials TO authenticated;
GRANT ALL ON TABLE public.shared_credentials TO service_role;


--
-- Name: TABLE shared_workflow; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.shared_workflow TO anon;
GRANT ALL ON TABLE public.shared_workflow TO authenticated;
GRANT ALL ON TABLE public.shared_workflow TO service_role;


--
-- Name: TABLE tag_entity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.tag_entity TO anon;
GRANT ALL ON TABLE public.tag_entity TO authenticated;
GRANT ALL ON TABLE public.tag_entity TO service_role;


--
-- Name: TABLE "user"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public."user" TO anon;
GRANT ALL ON TABLE public."user" TO authenticated;
GRANT ALL ON TABLE public."user" TO service_role;


--
-- Name: TABLE user_api_keys; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_api_keys TO anon;
GRANT ALL ON TABLE public.user_api_keys TO authenticated;
GRANT ALL ON TABLE public.user_api_keys TO service_role;


--
-- Name: TABLE user_channel; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_channel TO anon;
GRANT ALL ON TABLE public.user_channel TO authenticated;
GRANT ALL ON TABLE public.user_channel TO service_role;


--
-- Name: TABLE user_group; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_group TO anon;
GRANT ALL ON TABLE public.user_group TO authenticated;
GRANT ALL ON TABLE public.user_group TO service_role;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.users TO anon;
GRANT ALL ON TABLE public.users TO authenticated;
GRANT ALL ON TABLE public.users TO service_role;


--
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.users_id_seq TO anon;
GRANT ALL ON SEQUENCE public.users_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.users_id_seq TO service_role;


--
-- Name: TABLE variables; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.variables TO anon;
GRANT ALL ON TABLE public.variables TO authenticated;
GRANT ALL ON TABLE public.variables TO service_role;


--
-- Name: TABLE webhook_entity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.webhook_entity TO anon;
GRANT ALL ON TABLE public.webhook_entity TO authenticated;
GRANT ALL ON TABLE public.webhook_entity TO service_role;


--
-- Name: TABLE workflow_entity; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workflow_entity TO anon;
GRANT ALL ON TABLE public.workflow_entity TO authenticated;
GRANT ALL ON TABLE public.workflow_entity TO service_role;


--
-- Name: TABLE workflow_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workflow_history TO anon;
GRANT ALL ON TABLE public.workflow_history TO authenticated;
GRANT ALL ON TABLE public.workflow_history TO service_role;


--
-- Name: TABLE workflow_statistics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workflow_statistics TO anon;
GRANT ALL ON TABLE public.workflow_statistics TO authenticated;
GRANT ALL ON TABLE public.workflow_statistics TO service_role;


--
-- Name: TABLE workflows_tags; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workflows_tags TO anon;
GRANT ALL ON TABLE public.workflows_tags TO authenticated;
GRANT ALL ON TABLE public.workflows_tags TO service_role;


--
-- PostgreSQL database dump complete
--

