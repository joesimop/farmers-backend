from transformers import TFBertForSequenceClassification
from transformers import BertTokenizer, pipeline
import os, dotenv
class Model:
    def __init__(self):

        # NOTE THE MODEL IS ONLY LOCAL AND NOT ON THE REPO
        print("Loading model...")
        dotenv.load_dotenv()
        self.model = TFBertForSequenceClassification.from_pretrained("joesimop/rareconnect-text-classifier", token=os.environ.get("MODEL_TOKEN"))
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)
        self.model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        self.pipeline = pipeline('text-classification', model=self.model, tokenizer=self.tokenizer)

    def predict(self, text):
        return self.pipeline(text)

    # def train(self, data):
    #     data = pd.read_csv(data)
    #     data['text'] = data['text'].apply(clean_text)
    #     data['text'] = data['text'].apply(lambda x: ' '.join(x.split()[:512]))
    #     data['label'] = data['label'].apply(lambda x: 1 if x == 'positive' else 0)
    #     X_train, X_test, y_train, y_test = train_test_split(data['text'], data['label'], test_size=0.2, random_state=42)
    #     X_train = mask_inputs_for_bert(X_train, self.tokenizer)
    #     X_test = mask_inputs_for_bert(X_test, self.tokenizer)
    #     self.model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=1)
    #     self.model.save_weights('AI/weights.h5')