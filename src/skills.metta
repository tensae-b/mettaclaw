(= (getSkills)
   (;INTERNAL:
    "- Remember a particular string such as skills and memories: remember string"
    "- Query long-term embedding memory for skills and memories with short phrases only: query string"
    "- Episodes searches history for episodes around a time stamp, time format is same as in TIME: episodes time_string"
    "- Pin a certain string as short-term working memory item to keep track of task state: pin string"
    ;SHELL AND FILE I/O:
    "- Execute shell command without apostrophe in string, it returns the command output to you: shell string"
    "- Read file to string: read-file filename"
    "- Write string to file: write-file filename string"
    "- Append line to file: append-file filename string",
    ;COMMUNICATION CHANNELS:
    "- Send message to user: send string"
    "- Search the web: search string"
    "- Save client profile, branding, voice, constraints, and audience: (save-client-profile brand_in_quotes profile_in_quotes)"
    "- Read saved client profile: (client-profile brand_in_quotes)"
    "- List clients with saved campaign memory: (list-clients)"
    "- Save a previous campaign for a client: (add-client-campaign brand_in_quotes concept_in_quotes ideas_in_quotes)"
    "- Read previous campaign ideas for a client: (client-campaign-history brand_in_quotes)"
    "- Generate 3 campaign ideas using saved client profile and previous campaigns: (campaign-ideas brand_in_quotes concept_note_in_quotes)"
    ;CODE EXECUTION:
    "- Execute MeTTa expression: metta sexpression"
    "Example to invoke Non-Axiomatic Logic via MeTTa: "
    "metta (|- ((--> (× sam garfield) friend) (stv 1.0 0.9))"
    "          ((--> garfield animal) (stv 1.0 0.9)))"
    "metta (|- ((==> (--> (× $1 elephant) eat) (--> $1 ([] dangerous))) (stv 1.0 0.9))"
    "          ((--> (× tiger elephant) eat) (stv 1.0 0.9)))"
    "Also: note the $1 for independent variables, and for negated knowledge use (stv 0.0 0.9)"
    "Additionally |- also works for revision, to merge evidence even when the term of both premises is the same."))

(= (read-file $file)
   (progn (translatePredicate (exists_file $file))
          (translatePredicate (read_file_to_string $file $content ()))
          $content))

(= (write-file $file $str)
   (progn (translatePredicate (open $file write $Out))
          (translatePredicate (write $Out $str))
          (translatePredicate (close $Out))
          WRITE-FILE-SUCCESS))

(= (append-file $file $str)
   (progn (translatePredicate (exists_file $file))
          (translatePredicate (open $file append $Out))
          (translatePredicate (write $Out $str))
          (translatePredicate (nl $Out)),
          (translatePredicate (close $Out))
          APPEND-FILE-SUCCESS))

!(import_prolog_functions_from_file (library mettaclaw ./src/skills.pl) (shell first_char))

(= (metta $str)
   (let $code (sread $str)
        (repr (swrite (eval $code)))))

!(import! &self (library mettaclaw ./channels/campaign.py))

(= (campaign-ideas $brand $concept)
   (py-call (campaign.campaign_ideas $brand $concept)))

(= (save-client-profile $brand $profile)
   (py-call (campaign.save_client_profile $brand $profile)))

(= (client-profile $brand)
   (py-call (campaign.get_client_profile $brand)))

(= (list-clients)
   (py-call (campaign.list_clients)))

(= (add-client-campaign $brand $concept $ideas)
   (py-call (campaign.add_client_campaign $brand $concept $ideas)))

(= (client-campaign-history $brand)
   (py-call (campaign.client_campaign_history $brand)))

(= (pin $x)
   PIN-SUCCESS)
