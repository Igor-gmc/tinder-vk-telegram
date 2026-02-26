Table tg_users {
    tg_user_id bigint [pk, not null, note: 'Telegram user ID']
    vk_access_token text [note: 'VK токен пользователя']
    vk_user_id bigint [note: 'VK ID пользователя']
    filter_city_name varchar(128) [note: 'название города']
    filter_gender smallint [note: '0=любой, 1=жен, 2=муж']
    filter_age_from smallint [note: 'возраст ОТ']
    filter_age_to smallint [note: 'возраст ДО']
    history_cursor integer [default: 0, note: 'текущая позиция в view_history']
  }

  Table vk_profiles {
    vk_user_id bigint [pk, not null, note: 'VK ID кандидата']
    first_name varchar(128)
    last_name varchar(128)
    profile_url text [note: 'ссылка на профиль VK']
    status varchar(16) [default: 'new', note: 'new / processing / ready / error']
    found_at timestamptz [note: 'когда найден через users.search']
  }

  Table search_queue {
    id serial [pk, increment]
    tg_user_id bigint [not null, ref: > tg_users.tg_user_id]
    vk_profile_id bigint [not null, ref: > vk_profiles.vk_user_id]
    position integer [not null, note: 'порядок в результатах поиска']

    indexes {
      (tg_user_id, vk_profile_id) [unique]
      (tg_user_id, position)
    }
  }

  Table seen_profiles {
    id serial [pk, increment]
    tg_user_id bigint [not null, ref: > tg_users.tg_user_id]
    vk_profile_id bigint [not null, ref: > vk_profiles.vk_user_id]

    indexes {
      (tg_user_id, vk_profile_id) [unique]
      tg_user_id
    }
  }

  Table view_history {
    id serial [pk, increment]
    tg_user_id bigint [not null, ref: > tg_users.tg_user_id]
    vk_profile_id bigint [not null, ref: > vk_profiles.vk_user_id]
    position integer [not null, note: 'порядковый номер в истории']
    photo_attachments text [note: 'PostgreSQL TEXT ARRAY — фото attachments']

    indexes {
      (tg_user_id, position) [unique]
    }
  }

  Table favorite_profiles {
    id serial [pk, increment]
    tg_user_id bigint [not null, ref: > tg_users.tg_user_id]
    vk_profile_id bigint [not null, ref: > vk_profiles.vk_user_id]

    indexes {
      (tg_user_id, vk_profile_id) [unique]
      tg_user_id
    }
  }

  Table blacklist_profiles {
    id serial [pk, increment]
    tg_user_id bigint [not null, ref: > tg_users.tg_user_id]
    vk_profile_id bigint [not null, ref: > vk_profiles.vk_user_id]

    indexes {
      (tg_user_id, vk_profile_id) [unique]
      tg_user_id
    }
  }

  Table vk_photos {
    id serial [pk, increment]
    vk_user_id bigint [not null, ref: > vk_profiles.vk_user_id, note: 'владелец фото']
    vk_photo_id bigint [not null, note: 'ID фото в VK']
    likes_count integer [default: 0, note: 'лайки — ключ ранжирования']
    file_path text [note: 'путь к файлу на диске']
    downloaded_at timestamptz [note: 'когда скачали']

    status varchar(16) [default: 'raw', note: 'raw / accepted / rejected / selected']
    reject_reason varchar(32) [note: 'no_face, multi_face, blurry, small_face, low_score, error']  

    faces_count smallint [note: 'сколько лиц нашёл детектор']
    det_score real [note: 'уверенность детектора для выбранного лица']
    bbox jsonb [note: 'координаты лица — x1, y1, x2, y2']
    blur_score real [note: 'variance of Laplacian']

    embedding bytea [note: 'ArcFace 512 x float32 = 2048 bytes']
    embedding_normed boolean [default: false, note: 'эмбеддинг L2-нормирован']
    model_name varchar(64) [note: 'напр. buffalo_l']
    model_version varchar(32) [note: 'версия модели']
    processed_at timestamptz [note: 'когда обработали']

    indexes {
      (vk_user_id, vk_photo_id) [unique, note: 'не качать повторно']
      vk_user_id [note: 'группировка и выбор топ-3']
      status [note: 'фильтр по статусу обработки']
    }
  }